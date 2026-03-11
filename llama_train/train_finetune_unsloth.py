# -*- coding: utf-8 -*-
"""
Дообучение Llama с Unsloth (LoRA): быстрее и меньше VRAM.
Тот же датасет и выход — одна объединённая модель в OUTPUT_DIR.
Запуск отдельно: python train_finetune_unsloth.py (или через Docker с образом llama-train-unsloth).
"""
import os
import json
from pathlib import Path

from datasets import Dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments

# Те же переменные окружения, что и у обычного обучения
ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = os.environ.get("MODEL_PATH", str(ROOT / "model"))
TRAIN_JSONL = os.environ.get("TRAIN_DATASET", str(ROOT / "extremism_detection_dataset_number_char" / "train_dataset.jsonl"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", str(Path(__file__).resolve().parent / "output_unsloth"))

MAX_SEQ_LENGTH = 2048
BATCH_SIZE = 2
GRAD_ACCUM = 4
EPOCHS = 2
LR = 2e-5
LORA_R = 16
LORA_ALPHA = 16


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def build_text(example):
    instruction = example["instruction"]
    inp = example["input"]
    out = example["output"]
    prompt = f"{instruction}\n\nТекст для анализа:\n{inp}\n\nОтвет (только JSON, без пояснений):\n"
    return prompt + out


def main():
    print("Unsloth LoRA — путь к модели:", MODEL_PATH)
    print("Обучающий датасет:", TRAIN_JSONL)
    print("Выходная папка:", OUTPUT_DIR)

    data = load_jsonl(TRAIN_JSONL)
    print(f"Загружено примеров: {len(data)}")

    texts = [build_text(x) for x in data]
    dataset = Dataset.from_dict({"text": texts})

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_PATH,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=False,
        trust_remote_code=True,
    )
    FastLanguageModel.for_training(model)

    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        logging_steps=50,
        save_strategy="epoch",
        bf16=True,
        warmup_ratio=0.03,
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        tokenizer=tokenizer,
    )

    trainer.train()

    # Объединяем LoRA с базой — получаем одну модель без адаптеров (обязательно присвоить результат!)
    model = trainer.model
    if hasattr(model, "merge_and_unload"):
        model = model.merge_and_unload()
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("Модель (объединённая) сохранена в", OUTPUT_DIR)


if __name__ == "__main__":
    main()
