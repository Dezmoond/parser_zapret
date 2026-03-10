# -*- coding: utf-8 -*-
"""
Создаёт новые CSV-файлы без приставок аугментации из исходных датасетов.
Исходные файлы не изменяются. Новые: *_без_приставок.csv
Запуск: python strip_prefixes_from_csv.py
"""

import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent

# Те же приставки, что в strip_output_prefixes.py + доп. для организаций из blacklist/expanded
PERSONS_PREFIXES = [
    "по мнению ", "от ", "для ", "на имя ", "документ на ", "выдано ", "документ ",
]
ORGANIZATIONS_PREFIXES = [
    "согласно реестру ", "исключить из перечня ", "сторона по делу ", "согласно договору с ",
    "контракт с ", "в организации ", "направлено в ", "получено от ", "подразделение ",
    "в структуре ", "учёт в ", "лицензия ", "наименование: ", "в перечень ", "со стороны ",
    "в адрес ", "договор с ", "сотрудник ", "в лице ", "организация ", "истец ", "ответчик ",
    "заявитель ", "в ", "из ", "для ", "от ",
]
TITLES_PREFIXES = [
    "упоминается произведение «", "материал «", "информационный материал «",
    "книга «", "фильм «", "песня «", "роман «", "стихотворение «", "аудиозапись «",
    "видеофайл «", "видеозапись «", "листовка «", "«",
]
URLS_PREFIXES = [
    "подробнее: ", "источник: ", "см. ", "ссылка: ",
]


def strip_prefix(s: str, prefixes: list, case_insensitive: bool = True, repeat: bool = True) -> str:
    if not s or not isinstance(s, str):
        return s
    prev = None
    while prev != s:
        prev = s
        for p in sorted(prefixes, key=len, reverse=True):
            if not p:
                continue
            check = s.lower() if case_insensitive else s
            pre = p.lower() if case_insensitive else p
            if check.startswith(pre):
                s = s[len(p) :].strip()
                break
        if not repeat:
            break
    return s.strip()


def strip_title_tail(s: str) -> str:
    if not s:
        return s
    s = s.strip()
    if s.endswith("»."):
        s = s[:-2].strip()
    elif s.endswith("»"):
        s = s[:-1].strip()
    s = s.replace("» (", " (").replace("», ", ", ")
    if s.endswith("»"):
        s = s[:-1].strip()
    return s


def clean_text_by_label(text: str, label: str) -> str:
    label = (label or "").strip().lower()
    if not text:
        return text
    if label == "fio":
        return strip_prefix(text, PERSONS_PREFIXES)
    if label == "organization":
        return strip_prefix(text, ORGANIZATIONS_PREFIXES)
    if label == "title":
        t = strip_prefix(text, TITLES_PREFIXES)
        return strip_title_tail(t)
    if label == "url":
        return strip_prefix(text, URLS_PREFIXES)
    return text.strip()


def process_csv(in_path: Path, out_path: Path) -> int:
    count = 0
    with open(in_path, "r", encoding="utf-8", newline="") as fin:
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames
        if not fieldnames or "text" not in fieldnames:
            raise ValueError(f"В файле {in_path} нет колонки text")
        with open(out_path, "w", encoding="utf-8", newline="") as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                text = row.get("text", "")
                label = row.get("label", "")
                # Только поля из заголовка (избегаем ключа None при лишних столбцах)
                out_row = {k: row.get(k, "") for k in fieldnames}
                out_row["text"] = clean_text_by_label(text, label)
                writer.writerow(out_row)
                count += 1
    return count


def main():
    pairs = [
        (BASE / "dataset_01_expanded_only_white.csv", BASE / "dataset_01_expanded_only_white_без_приставок.csv"),
        (BASE / "blacklist.csv", BASE / "blacklist_без_приставок.csv"),
    ]
    for in_path, out_path in pairs:
        if not in_path.exists():
            print(f"Пропуск (нет файла): {in_path}")
            continue
        n = process_csv(in_path, out_path)
        print(f"Создан: {out_path.name} ({n} строк) из {in_path.name}")


if __name__ == "__main__":
    main()
