# -*- coding: utf-8 -*-
"""Убирает из поля input спецсимволы \\n и \\t (замена на пробел, схлопывание пробелов)."""
import json
import os
import re

DIR = os.path.dirname(os.path.abspath(__file__))


def normalize_text(s: str) -> str:
    """Заменяем \\n и \\t на пробел, схлопываем повторяющиеся пробелы."""
    s = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    return re.sub(r" +", " ", s).strip()


def process(path: str) -> int:
    tmp = path + ".tmp"
    n = 0
    with open(path, "r", encoding="utf-8") as f, open(tmp, "w", encoding="utf-8") as out:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            obj["input"] = normalize_text(obj["input"])
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n += 1
    os.replace(tmp, path)
    return n


if __name__ == "__main__":
    train_path = os.path.join(DIR, "train_dataset.jsonl")
    test_path = os.path.join(DIR, "test_dataset.jsonl")
    n_train = process(train_path)
    n_test = process(test_path)
    print("Нормализовано поле input: \\n \\t \\r -> пробел, схлопнуты пробелы.")
    print("train_dataset.jsonl:", n_train, "строк")
    print("test_dataset.jsonl:", n_test, "строк")
