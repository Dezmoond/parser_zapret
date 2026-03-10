# -*- coding: utf-8 -*-
"""
Заменяет категорию на «ЛГБТ» для строк, где в экстремистских фразах встречаются
слова/фразы: геи, гомосексуализм, лгбт, лесбиянки, прайд, квир и т.п.
Обрабатывает:
  - extremism_detection_dataset_number_char/train_dataset.jsonl, test_dataset.jsonl
  - extremism_detection_dataset/train_dataset.jsonl, test_dataset.jsonl
Запуск из корня проекта: python extremism_detection_dataset_number_char/set_lgbt_category.py
"""
import json
import os
import re

# Ключевые слова/фразы для категории ЛГБТ (регистронезависимый поиск по фразе)
LGBT_KEYWORDS = [
    "геи", "гей", "гомосексуал", "лесбиянк", "лгбт", "прайд", "квир",
    "трансгендер", "голубой", "розовый", "педераст", "содом",
    "lgbt", "gay", "lesbian", "pride", "queer", "trans",
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = [
    os.path.join(ROOT, "extremism_detection_dataset_number_char", "train_dataset.jsonl"),
    os.path.join(ROOT, "extremism_detection_dataset_number_char", "test_dataset.jsonl"),
    os.path.join(ROOT, "extremism_detection_dataset", "train_dataset.jsonl"),
    os.path.join(ROOT, "extremism_detection_dataset", "test_dataset.jsonl"),
]


def phrase_text(p) -> str:
    """Текст фразы: из объекта с полем text или сама строка."""
    if isinstance(p, dict):
        return (p.get("text") or p.get("phrase") or "").strip()
    return str(p).strip()


def has_lgbt_phrase(phrases) -> bool:
    """Есть ли среди фраз хотя бы одна с ЛГБТ-ключевым словом."""
    for p in phrases or []:
        text = phrase_text(p).lower()
        if not text:
            continue
        for kw in LGBT_KEYWORDS:
            if kw in text:
                return True
    return False


def update_categories_for_lgbt(categories: list) -> list:
    """Добавляем ЛГБТ, убираем расизм (для строк с ЛГБТ-фразами категорию заменяем/дополняем)."""
    cats = list(categories or [])
    if "ЛГБТ" not in cats:
        cats.append("ЛГБТ")
    # Убираем расизм, если он был ошибочно поставлен вместо ЛГБТ
    if "расизм" in cats:
        cats.remove("расизм")
    return cats


def process(path: str, backup: bool = True) -> int:
    """Обрабатывает один jsonl-файл. Возвращает число изменённых строк."""
    if not os.path.isfile(path):
        return 0
    if backup:
        bak = path + ".bak"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(bak, "w", encoding="utf-8") as f:
            f.write(content)
    tmp = path + ".tmp"
    n_changed = 0
    with open(path, "r", encoding="utf-8") as f, open(tmp, "w", encoding="utf-8") as out:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out_str = obj.get("output", "{}")
            try:
                out_obj = json.loads(out_str)
            except json.JSONDecodeError:
                out.write(json.dumps(obj, ensure_ascii=False) + "\n")
                continue

            phrases = out_obj.get("extremist_phrases") or []
            if not has_lgbt_phrase(phrases):
                out.write(json.dumps(obj, ensure_ascii=False) + "\n")
                continue

            new_cats = update_categories_for_lgbt(out_obj.get("categories"))
            out_obj["categories"] = new_cats
            obj["output"] = json.dumps(out_obj, ensure_ascii=False)
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n_changed += 1
    os.replace(tmp, path)
    return n_changed


if __name__ == "__main__":
    for path in FILES:
        n = process(path, backup=True)
        print(path, "— заменено категорий на ЛГБТ:", n)
    print("Готово. Бэкапы: *.jsonl.bak")
