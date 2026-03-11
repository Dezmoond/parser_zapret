# -*- coding: utf-8 -*-
"""
Тестирование дообученной Llama на датасете обнаружения экстремизма.
Подходит для модели из обычного обучения (output) и для объединённой модели Unsloth (output_unsloth).
Читает test_dataset.jsonl, для каждого примера: ввод, эталонный output, ответ модели, сравнение.
Метрики: accuracy, precision, recall, F1, матрица путаницы (по полю found_dangerous).
Все результаты — в терминал и в лог-файл.
"""
import os
import re
import json
import torch
from pathlib import Path
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForCausalLM
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score, classification_report

ROOT = Path(__file__).resolve().parent.parent.parent
# По умолчанию — объединённая модель Unsloth (output_unsloth). Для базовой: MODEL_PATH=.../output
MODEL_PATH = os.environ.get("MODEL_PATH", str(Path(__file__).resolve().parent / "output_unsloth"))
BASE_MODEL_PATH = os.environ.get("BASE_MODEL_PATH", "")
TEST_JSONL = os.environ.get("TEST_DATASET", str(ROOT / "extremism_detection_dataset" / "test_dataset.jsonl"))
LOG_FILE = os.environ.get("EVAL_LOG", str(Path(__file__).resolve().parent / "evaluation.log"))
# Ограничение числа примеров (0 или не задано — все). Пример: MAX_TEST_SAMPLES=2000
MAX_TEST_SAMPLES = int(os.environ.get("MAX_TEST_SAMPLES", "0") or "0")

MAX_NEW_TOKENS = 2048
MAX_INPUT_DISPLAY = 2048


def log_print(f, msg):
    print(msg)
    f.write(msg + "\n")
    f.flush()


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def parse_expected_output(output_str):
    """Из эталонного output (JSON-строка) извлекаем found_dangerous и при необходимости фразы."""
    try:
        d = json.loads(output_str)
        return d.get("found_dangerous", None), d
    except Exception:
        return None, None


def extract_found_dangerous_from_model_reply(text):
    """Пытаемся извлечь found_dangerous из ответа модели (может быть внутри JSON или в тексте)."""
    text = text.strip()
    try:
        if "```json" in text:
            text = re.sub(r"```json\s*", "", text)
            text = re.sub(r"```\s*$", "", text)
        d = json.loads(text)
        return d.get("found_dangerous", None)
    except Exception:
        pass
    m = re.search(r'"found_dangerous"\s*:\s*(true|false)', text, re.IGNORECASE)
    if m:
        return m.group(1).lower() == "true"
    m = re.search(r"found_dangerous\s*:\s*(true|false)", text, re.IGNORECASE)
    if m:
        return m.group(1).lower() == "true"
    return None


def generate_reply(tokenizer, model, device, instruction, input_text):
    """Генерация ответа модели по instruction + input (формат как при обучении/чате)."""
    prompt = f"{instruction}\n\nТекст для анализа:\n{input_text}\n\nОтвет (только JSON, без пояснений):\n"
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(device)
    pad_id = model.config.pad_token_id if model.config.pad_token_id is not None else tokenizer.eos_token_id
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            top_p=0.9,
            temperature=0.3,
            pad_token_id=pad_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    reply = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return reply


def similarity_description(expected_bool, predicted_bool):
    """Краткое описание совпадения по found_dangerous."""
    if expected_bool is None or predicted_bool is None:
        return "не удалось извлечь"
    if expected_bool == predicted_bool:
        return "совпадает"
    return "не совпадает"


def main():
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log_print(log, "=" * 60)
        log_print(log, f"Дата запуска: {datetime.now().isoformat()}")
        log_print(log, f"Модель: {MODEL_PATH}")
        log_print(log, f"Тестовый датасет: {TEST_JSONL}")
        log_print(log, f"Лог-файл: {LOG_FILE}")
        log_print(log, "=" * 60)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        log_print(log, f"Устройство: {device}")

        # Как в чате: полная модель (config.json с model_type) или база + адаптер
        config_path = os.path.join(MODEL_PATH, "config.json")
        has_full_model = False
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if cfg.get("model_type"):
                    has_full_model = True
            except Exception:
                pass

        if has_full_model:
            log_print(log, "Загрузка модели (объединённая)...")
            tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True).to(device)
        else:
            base_path = BASE_MODEL_PATH.strip()
            if not base_path or not os.path.isdir(base_path):
                log_print(log, "Ошибка: в каталоге модели нет config.json (только адаптер). Задайте BASE_MODEL_PATH и смонтируйте базовую модель.")
                log_print(log, "Пример Docker: -v \"путь/к/Llama-3.2-3B-Instruct:/model\" -e BASE_MODEL_PATH=/model")
                raise SystemExit(1)
            log_print(log, f"Загрузка базовой модели из {base_path} и адаптера из {MODEL_PATH}...")
            tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True)
            base_model = AutoModelForCausalLM.from_pretrained(base_path, local_files_only=True, trust_remote_code=True)
            adapter_config_path = os.path.join(MODEL_PATH, "adapter_config.json")
            adapter_config_orig = None
            if os.path.isfile(adapter_config_path):
                with open(adapter_config_path, "r", encoding="utf-8") as f:
                    adapter_config_orig = f.read()
                if "/model" in adapter_config_orig:
                    with open(adapter_config_path, "w", encoding="utf-8") as f:
                        f.write(adapter_config_orig.replace('"/model"', json.dumps(base_path)).replace("'/model'", json.dumps(base_path)))
            try:
                from peft import PeftModel
                model = PeftModel.from_pretrained(base_model, MODEL_PATH, is_trainable=False)
                model = model.merge_and_unload()
            finally:
                if adapter_config_orig is not None:
                    with open(adapter_config_path, "w", encoding="utf-8") as f:
                        f.write(adapter_config_orig)
            model = model.to(device)
            log_print(log, "Адаптер загружен и объединён с базой.")

        if model.config.pad_token_id is None:
            model.config.pad_token_id = tokenizer.eos_token_id
        if isinstance(model.config.pad_token_id, list):
            model.config.pad_token_id = model.config.pad_token_id[0]

        test_data = load_jsonl(TEST_JSONL)
        if MAX_TEST_SAMPLES > 0:
            test_data = test_data[:MAX_TEST_SAMPLES]
            log_print(log, f"Тест на первых {len(test_data)} примерах (MAX_TEST_SAMPLES={MAX_TEST_SAMPLES})")
        log_print(log, f"Загружено тестовых примеров: {len(test_data)}\n")

        expected_bools = []
        predicted_bools = []

        for idx, row in enumerate(test_data):
            instruction = row["instruction"]
            input_text = row["input"]
            expected_output_str = row["output"]

            exp_found, _ = parse_expected_output(expected_output_str)
            reply = generate_reply(tokenizer, model, device, instruction, input_text)
            pred_found = extract_found_dangerous_from_model_reply(reply)
            if pred_found is None:
                pred_found = False

            if exp_found is not None:
                expected_bools.append(exp_found)
                predicted_bools.append(pred_found)

            input_display = input_text[:MAX_INPUT_DISPLAY] + ("..." if len(input_text) > MAX_INPUT_DISPLAY else "")
            sim = similarity_description(exp_found, pred_found)

            log_print(log, f"--- Пример {idx + 1} ---")
            log_print(log, f"Ввод (начало): {input_display}")
            log_print(log, f"Эталонный output: {expected_output_str[:500]}{'...' if len(expected_output_str) > 500 else ''}")
            log_print(log, f"Ответ модели: {reply[:500]}{'...' if len(reply) > 500 else ''}")
            log_print(log, f"Сравнение (found_dangerous): эталон={exp_found}, модель={pred_found} -> {sim}")
            log_print(log, "")

        # Метрики по бинарной классификации found_extremism
        log_print(log, "\n" + "=" * 60)
        log_print(log, "МЕТРИКИ (found_dangerous)")
        log_print(log, "=" * 60)

        if not expected_bools:
            log_print(log, "Нет валидных эталонных ответов для подсчёта метрик.")
        else:
            acc = accuracy_score(expected_bools, predicted_bools)
            prec = precision_score(expected_bools, predicted_bools, zero_division=0)
            rec = recall_score(expected_bools, predicted_bools, zero_division=0)
            f1 = f1_score(expected_bools, predicted_bools, zero_division=0)

            log_print(log, f"Число примеров с валидным эталоном: {len(expected_bools)}")
            log_print(log, f"Accuracy:  {acc:.4f}")
            log_print(log, f"Precision: {prec:.4f}")
            log_print(log, f"Recall:    {rec:.4f}")
            log_print(log, f"F1:        {f1:.4f}")

            report = classification_report(expected_bools, predicted_bools, target_names=["no_dangerous", "dangerous"], zero_division=0)
            log_print(log, "\nClassification report:\n" + report)

            cm = confusion_matrix(expected_bools, predicted_bools)
            log_print(log, "Матрица путаницы (строки: эталон, столбцы: предсказание):")
            log_print(log, "              pred_no  pred_yes")
            if cm.shape == (2, 2):
                log_print(log, f"true_no       {cm[0][0]:6d}  {cm[0][1]:6d}")
                log_print(log, f"true_yes      {cm[1][0]:6d}  {cm[1][1]:6d}")
            elif cm.shape == (1, 2):
                log_print(log, f"true_no       {cm[0][0]:6d}  {cm[0][1]:6d}")
                log_print(log, "true_yes        0      0")
            elif cm.size == 1:
                log_print(log, f"true_no/yes   {cm.flat[0]:6d}      0")
            else:
                log_print(log, str(cm))
        log_print(log, "\nГотово. Лог сохранён в " + LOG_FILE)


if __name__ == "__main__":
    main()
