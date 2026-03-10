# -*- coding: utf-8 -*-
"""Перемешивает строки CSV (кроме заголовка). Запуск: python shuffle_dataset.py"""
import csv
import random
from pathlib import Path

BASE = Path(__file__).resolve().parent
CSV_PATH = BASE / "dataset_01_expanded_only_white.csv"
RANDOM_SEED = 42

def main():
    if not CSV_PATH.exists():
        print(f"Файл не найден: {CSV_PATH}")
        return
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    random.seed(RANDOM_SEED)
    random.shuffle(rows)
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Готово. Перемешано {len(rows)} строк в {CSV_PATH}.")

if __name__ == "__main__":
    main()
