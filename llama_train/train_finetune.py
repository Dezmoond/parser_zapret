# -*- coding: utf-8 -*-
"""
Дообучение Llama-3.2-3B-Instruct на датасете обнаружения экстремизма.
Формат датасета: instruction + input -> output (JSON).
Запуск: см. README или Dockerfile.train.
"""
import os
import json
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DefaultDataCollator
from datasets import Dataset

# Пути: из переменных окружения (Docker) или относительно корня проекта
ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = os.environ.get("MODEL_PATH", str(ROOT / "model"))
TRAIN_JSONL = os.environ.get("TRAIN_DATASET", str(ROOT / "extremism_detection_dataset_number_char" / "train_dataset.jsonl"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", str(Path(__file__).resolve().parent / "output"))

# Параметры обучения под RTX 4060 Ti (8 GB VRAM; при 16 GB можно BATCH_SIZE=2, MAX_LENGTH=1024)
MAX_LENGTH = 512       # меньше токенов — быстрее шаг (attention O(n²))
BATCH_SIZE = 1
GRAD_ACCUM = 8         # эффективный батч = 8
EPOCHS = 1
LR = 2e-5
MAX_GRAD_NORM = 1.0
WARMUP_RATIO = 0.03
FREEZE_LAYERS = 6      # заморозить первые N слоёв


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def build_prompt_completion(example):
    """Формируем один текст: промпт + ответ (для causal LM считаем только loss по ответу)."""
    instruction = example["instruction"]
    inp = example["input"]
    out = example["output"]
    prompt = f"{instruction}\n\nТекст для анализа:\n{inp}\n\nОтвет (только JSON, без пояснений):\n"
    return prompt, out


def tokenize_for_causal_lm(examples, tokenizer, max_length):
    """Токенизация: промпт + ответ; в labels только ответ (промпт помечен -100)."""
    prompts = []
    completions = []
    for i in range(len(examples["instruction"])):
        prompt, completion = build_prompt_completion({
            "instruction": examples["instruction"][i],
            "input": examples["input"][i],
            "output": examples["output"][i],
        })
        prompts.append(prompt)
        completions.append(completion)

    full_texts = [p + c for p, c in zip(prompts, completions)]
    enc = tokenizer(
        full_texts,
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_tensors=None,
    )
    prompt_enc = tokenizer(
        prompts,
        truncation=True,
        max_length=max_length,
        padding=False,
        return_tensors=None,
    )

    pad_id = tokenizer.pad_token_id
    labels = []
    for j in range(len(full_texts)):
        prompt_len = len(prompt_enc["input_ids"][j])
        seq = enc["input_ids"][j]
        lab = [-100] * len(seq)
        for k in range(prompt_len, len(seq)):
            lab[k] = seq[k] if (pad_id is None or seq[k] != pad_id) else -100
        labels.append(lab)

    enc["labels"] = labels
    return enc


def _get_attn_implementation():
    """Flash Attention 2 если установлен, иначе SDPA (тоже ускоряет на PyTorch 2+)."""
    if not torch.cuda.is_available():
        return None
    try:
        import flash_attn  # noqa: F401
        return "flash_attention_2"
    except ImportError:
        return "sdpa"


def main():
    print("Путь к модели:", MODEL_PATH)
    print("Обучающий датасет:", TRAIN_JSONL)
    print("Выходная папка:", OUTPUT_DIR)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    attn_impl = _get_attn_implementation()
    if attn_impl:
        print("Attention:", attn_impl)
    # bf16 на PyTorch 2.4 + RTX 40xx даёт ускорение без проблем GradScaler (в отличие от fp32)
    model_dtype = torch.bfloat16 if torch.cuda.is_available() else None
    model_kw = {"local_files_only": True, "torch_dtype": model_dtype}
    if attn_impl:
        model_kw["attn_implementation"] = attn_impl
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, **model_kw)
    if isinstance(model.config.pad_token_id, list):
        model.config.pad_token_id = model.config.pad_token_id[0]
    if model.config.pad_token_id is None:
        model.config.pad_token_id = tokenizer.eos_token_id

    cuda_available = torch.cuda.is_available()
    device = torch.device("cuda" if cuda_available else "cpu")
    if cuda_available:
        print("Устройство: CUDA (GPU)", torch.cuda.get_device_name(0))
    else:
        print("Устройство: CPU (GPU не обнаружена!)")
        if os.environ.get("MODEL_PATH") == "/model":
            print("ВНИМАНИЕ: Запуск в Docker без GPU. Нужны: nvidia-container-toolkit и флаг --gpus all.")
        raise SystemExit("Обучение LLM на CPU недопустимо. Настройте доступ к GPU в Docker или запускайте без Docker.")
    model.to(device)
    model.gradient_checkpointing_enable()  # экономия видеопамяти (RTX 4060 Ti 8 GB)

    # Заморозить часть слоёв (как в FINETUNELLAMA-QA)
    for name, param in model.named_parameters():
        if "model.layers" in name:
            try:
                layer_idx = int(name.split(".")[2])
                if layer_idx < FREEZE_LAYERS:
                    param.requires_grad = False
            except (IndexError, ValueError):
                pass

    data = load_jsonl(TRAIN_JSONL)
    print(f"Загружено примеров: {len(data)}")

    dataset_dict = {
        "instruction": [x["instruction"] for x in data],
        "input": [x["input"] for x in data],
        "output": [x["output"] for x in data],
    }
    dataset = Dataset.from_dict(dataset_dict)

    def tokenize_fn(examples):
        return tokenize_for_causal_lm(examples, tokenizer, MAX_LENGTH)

    tokenized = dataset.map(tokenize_fn, batched=True, remove_columns=dataset.column_names)

    # warmup_steps вместо устаревшего warmup_ratio (deprecated в transformers v5.2)
    total_steps = (len(tokenized) // (BATCH_SIZE * GRAD_ACCUM)) * EPOCHS
    warmup_steps = max(0, int(total_steps * WARMUP_RATIO))

    # bf16: быстрее fp32, на PyTorch 2.4 и RTX 40xx работает стабильно
    use_bf16 = torch.cuda.is_available()
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        warmup_steps=warmup_steps,
        max_grad_norm=MAX_GRAD_NORM,
        logging_steps=50,
        save_strategy="epoch",
        fp16=False,
        bf16=use_bf16,
        report_to="none",
    )

    data_collator = DefaultDataCollator()

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=data_collator,
    )

    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("Модель сохранена в", OUTPUT_DIR)


if __name__ == "__main__":
    main()
