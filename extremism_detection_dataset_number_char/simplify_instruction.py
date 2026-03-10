# -*- coding: utf-8 -*-
"""Замена длинной инструкции на короткую в train и test датасетах."""
import json
import os

DIR = os.path.dirname(os.path.abspath(__file__))
OLD_INSTRUCTION = "Проанализируй текст и найди все фразы экстремистского содержания, ненависти или призывы к насилию. Верни JSON с полями: found_extremism (true/false), extremist_phrases (массив найденных фраз), categories (массив категорий экстремизма)."
NEW_INSTRUCTION = "Определи экстремизм в тексте. Ответ — JSON: found_extremism, extremist_phrases, categories."


def process(path: str) -> int:
    tmp = path + ".tmp"
    n = 0
    with open(path, "r", encoding="utf-8") as f, open(tmp, "w", encoding="utf-8") as out:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            obj["instruction"] = NEW_INSTRUCTION
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n += 1
    os.replace(tmp, path)
    return n


if __name__ == "__main__":
    train_path = os.path.join(DIR, "train_dataset.jsonl")
    test_path = os.path.join(DIR, "test_dataset.jsonl")
    n_train = process(train_path)
    n_test = process(test_path)
    print("Новая инструкция:", NEW_INSTRUCTION)
    print("train_dataset.jsonl:", n_train, "строк")
    print("test_dataset.jsonl:", n_test, "строк")
