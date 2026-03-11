# -*- coding: utf-8 -*-
"""
Ручное тестирование модели, дообученной Unsloth (объединённая LoRA).
Режим чата: пользователь вводит только текст для анализа; инструкция подставляется автоматически.
Поддерживаются: 1) полная объединённая модель (config.json в MODEL_PATH); 2) только адаптер — тогда задайте BASE_MODEL_PATH.
Запуск: python chat_unsloth.py  (или MODEL_PATH=... [BASE_MODEL_PATH=...] python chat_unsloth.py)
"""
import os
import json
import re
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM

ROOT = Path(__file__).resolve().parent.parent.parent
# По умолчанию — объединённая модель или адаптер из output_unsloth
MODEL_PATH = os.environ.get("MODEL_PATH", str(Path(__file__).resolve().parent / "output_unsloth"))
BASE_MODEL_PATH = os.environ.get("BASE_MODEL_PATH", "")

MAX_NEW_TOKENS = 2048
# Инструкция в формате датасета: found_dangerous, dangerous_phrases (без categories)
INSTRUCTION = (
    "Определи экстремизм в тексте. Ответ — строго один JSON-объект с полями: found_dangerous (true/false), "
    "dangerous_phrases (массив строк или объектов с text, start_char, end_char). "
    "К опасному содержанию относится экстремизм, расизм, национализм, призывы ЛГБТ (запрещённая организация), "
    "упоминание Meta, Facebook, Instagram, WhatsApp (в любом написании). Правило: если найдена хотя бы одна опасная фраза — "
    "found_dangerous должен быть true; если found_dangerous false — массив dangerous_phrases пустой. "
    "Не пиши примечаний, пояснений и текста после JSON — только JSON."
)


def build_prompt(text_for_analysis: str) -> str:
    """Формат как при обучении: инструкция + текст + приглашение к ответу."""
    return f"{INSTRUCTION}\n\nТекст для анализа:\n{text_for_analysis}\n\nОтвет (только JSON, без примечаний и пояснений):\n"


def generate_reply(tokenizer, model, device, text_for_analysis: str) -> str:
    text_for_analysis = str(text_for_analysis or "").strip()
    prompt = str(build_prompt(text_for_analysis))
    if not prompt:
        return "{}"
    # Токенайзер ожидает одну строку (не list); нормализуем UTF-8
    prompt = prompt.encode("utf-8", errors="replace").decode("utf-8")
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=2048,
    ).to(device)
    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        pad_id = tokenizer.eos_token_id
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
    reply = tokenizer.decode(out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True).strip()
    return reply


def extract_first_json(raw: str) -> str:
    """Извлекает первый полный JSON из ответа модели и убирает примечания/пояснения."""
    s = raw.strip()
    if "```json" in s:
        s = re.sub(r"```json\s*", "", s)
        s = re.sub(r"```\s*$", "", s)
    start = s.find("{")
    if start == -1:
        return raw
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return raw


def fix_found_dangerous_consistency(data: dict) -> dict:
    """Если есть фразы в dangerous_phrases — found_dangerous должен быть true."""
    phrases = data.get("dangerous_phrases") or []
    if isinstance(phrases, list) and len(phrases) > 0 and data.get("found_dangerous") is False:
        data = dict(data)
        data["found_dangerous"] = True
    return data


def try_format_json(raw: str) -> str:
    """Извлекает первый JSON, исправляет противоречие found_dangerous/фразы, форматирует."""
    json_str = extract_first_json(raw)
    try:
        d = json.loads(json_str)
        d = fix_found_dangerous_consistency(d)
        return json.dumps(d, ensure_ascii=False, indent=2)
    except Exception:
        return raw


def main():
    print("Путь к модели (Unsloth):", MODEL_PATH)
    if not os.path.isdir(MODEL_PATH):
        print("Ошибка: папка модели не найдена. Укажите MODEL_PATH или обучите модель (train_finetune_unsloth.py).")
        return

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # Полная модель — только если есть config.json с ключом model_type (llama и т.д.)
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
        # Полная объединённая модель (config.json есть)
        print("Загрузка токенайзера и модели (объединённая)...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True).to(device)
    else:
        # Только адаптер LoRA — нужна базовая модель
        base_path = BASE_MODEL_PATH.strip()
        if not base_path or not os.path.isdir(base_path):
            print("В каталоге модели нет config.json (сохранён только адаптер). Укажите BASE_MODEL_PATH — путь к базовой Llama.")
            print("Пример (Docker): -e BASE_MODEL_PATH=/model  и смонтируйте каталог с базовой моделью в /model")
            return
        print("Загрузка базовой модели из", base_path)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True)
        base_model = AutoModelForCausalLM.from_pretrained(base_path, local_files_only=True, trust_remote_code=True)
        # Патчим adapter_config.json: /model -> base_path, чтобы PEFT не лез в Hub
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
        print("Адаптер загружен и объединён с базой.")

    if model.config.pad_token_id is None:
        model.config.pad_token_id = tokenizer.eos_token_id
    print("Готово. Вводите только текст для анализа (пустая строка или 'выход' — завершение).\n")

    while True:
        try:
            raw = input("Текст для анализа: ")
            text = str(raw.decode("utf-8") if isinstance(raw, bytes) else raw).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break
        if not text or text.lower() in ("выход", "exit", "quit", "q"):
            print("Выход.")
            break

        reply = generate_reply(tokenizer, model, device, text)
        # Показываем только первый JSON без примечаний; при противоречии (фразы есть, а found_dangerous false) — исправляем
        output = try_format_json(reply)
        print("Ответ:", output)
        print()


if __name__ == "__main__":
    main()
