# -*- coding: utf-8 -*-
"""
Создаёт датасет класса "other" на основе текста курсовая.txt:
извлекает слова и фразы (1–6 слов), нормализует (как в dataset_01_expanded_only_white),
отфильтровывает URL-подобное, дедуплицирует и добавляет 30 000 строк в CSV.
Запуск: python build_other_from_kursovaya.py
"""
import re
import csv
import random
from pathlib import Path

BASE = Path(__file__).resolve().parent
KURSOVAYA = BASE / "курсовая.txt"
CSV_PATH = BASE / "dataset_01_expanded_only_white.csv"
TARGET_OTHER_COUNT = 30_000
RANDOM_SEED = 42

# Подстроки, при наличии которых фраза не считается "other" (похожа на организацию, ФИО и т.д.)
OTHER_STOP_SUBSTRINGS = [
    "ао суэк", "суэк", "оао ", "пао ", "ооо ", "зао ", "ип ", " мгу ", "мгу им",
    "мельниченко", "андрей игоревич", "игоревич мельниченко",
    "кузбассразрезуголь", "сдс уголь", "мечел", "газпром", "лукойл", "роснефть",
    "сбербанк", "ржд", "дикси", "магнит", "яндекс", "тинькофф", "башнефть",
    "новосибирский государственный", "сибирская угольная",
    "http", ".ru", ".com", "wikipedia",
]


def looks_like_entity(phrase):
    """True, если фраза похожа на организацию/ФИО/url — не помечаем как other."""
    low = phrase.lower()
    return any(stop in low for stop in OTHER_STOP_SUBSTRINGS)


def normalize_text(text):
    """Как в RUBERT/normalize_text: нижний регистр, только буквы (лат/кириллица), цифры, пробелы."""
    if not text or not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^a-zа-яё0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_words_and_phrases(text, min_words=1, max_words=6):
    """Разбивает текст на слова, возвращает множество нормализованных слов и n-грамм (фраз)."""
    normalized = normalize_text(text)
    words = [w for w in normalized.split() if len(w) > 0]
    seen = set()
    n = len(words)
    for length in range(min_words, min(max_words + 1, n + 1)):
        for i in range(n - length + 1):
            phrase = " ".join(words[i : i + length])
            if len(phrase) < 2:
                continue
            if "http" in phrase or phrase.isdigit():
                continue
            seen.add(phrase)
    return seen, words


def main():
    if not KURSOVAYA.exists():
        print(f"Файл не найден: {KURSOVAYA}")
        return

    print("Чтение курсовая.txt...")
    with open(KURSOVAYA, "r", encoding="utf-8") as f:
        text = f.read()

    print("Извлечение слов и фраз (1–6 слов)...")
    candidates, word_list = extract_words_and_phrases(text, min_words=1, max_words=6)

    # Исключаем короткие, URL и фразы, похожие на организации/ФИО
    filtered = [
        p for p in candidates
        if len(p) >= 2
        and "http" not in p
        and not p.replace(" ", "").isdigit()
        and not looks_like_entity(p)
    ]

    random.seed(RANDOM_SEED)
    other_rows = list(filtered)
    # Если не хватает до 30k — добиваем случайными фразами из слов того же текста (2–4 слова)
    if len(other_rows) < TARGET_OTHER_COUNT:
        vocab = [w for w in set(word_list) if len(w) > 1 and w.isalpha() and not looks_like_entity(w)][:5000]
        need = TARGET_OTHER_COUNT - len(other_rows)
        extra = set()
        while len(extra) < need:
            k = random.randint(2, 4)
            phrase = " ".join(random.choices(vocab, k=k))
            if len(phrase) >= 3 and not looks_like_entity(phrase):
                extra.add(phrase)
        other_rows = other_rows + list(extra)[:need]
    else:
        random.shuffle(other_rows)
        other_rows = other_rows[:TARGET_OTHER_COUNT]

    other_rows = list(dict.fromkeys(other_rows))[:TARGET_OTHER_COUNT]
    print(f"Уникальных кандидатов other: {len(other_rows)}.")

    if not CSV_PATH.exists():
        print(f"Файл не найден: {CSV_PATH}")
        return

    print(f"Чтение существующего датасета {CSV_PATH}...")
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        all_rows = list(reader)

    # Удаляем старые строки с label=other и добавляем новые отфильтрованные
    existing = [row for row in all_rows if row.get("label", "").strip() != "other"]
    existing_set = {normalize_text(row.get("text", "")) for row in existing}
    to_add = [p for p in other_rows if p not in existing_set][:TARGET_OTHER_COUNT]
    print(f"Добавляем {len(to_add)} новых строк с меткой other (без дубликатов с существующими).")

    if not to_add:
        print("Нет новых фраз для добавления.")
        return

    other_dicts = [{"text": phrase, "label": "other"} for phrase in to_add]
    all_rows = existing + other_dicts
    random.shuffle(all_rows)

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_rows)

    print(f"Готово. Добавлено {len(to_add)} строк other. Всего строк: {len(all_rows)}. Датасет перемешан.")


if __name__ == "__main__":
    main()
