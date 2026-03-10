# -*- coding: utf-8 -*-
"""
Удаление приставок аугментации из значений в поле output JSONL-файлов.
Приставки заданы так же, как при аугментации CSV (add_other_class, build_addition_from_sources,
generate_dataset_01_expanded, blacklist/build_blacklist_dataset).
Запуск: python strip_output_prefixes.py
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent

# Приставки для persons (ФИО) — убираем с начала строки (регистронезависимо)
PERSONS_PREFIXES = [
    "по мнению ", "от ", "для ", "на имя ", "документ на ", "выдано ", "документ ",
]

# Приставки для organizations — длинные сначала
ORGANIZATIONS_PREFIXES = [
    "согласно реестру ", "исключить из перечня ", "согласно договору с ", "контракт с ",
    "в организации ", "направлено в ", "получено от ", "подразделение ", "в структуре ",
    "учёт в ", "лицензия ", "наименование: ", "в перечень ", "со стороны ", "в адрес ",
    "договор с ", "сотрудник ", "в лице ", "организация ", "в ", "из ", "для ", "от ",
]

# Приставки для titles (книги/фильмы/песни)
TITLES_PREFIXES = [
    "упоминается произведение «", "материал «", "информационный материал «",
    "книга «", "фильм «", "песня «", "роман «", "стихотворение «", "аудиозапись «",
    "видеофайл «", "видеозапись «", "листовка «", "«",
]

# Приставки для urls
URLS_PREFIXES = [
    "подробнее: ", "источник: ", "см. ", "ссылка: ",
]


def strip_prefix(s: str, prefixes: list, case_insensitive: bool = True) -> str:
    """Удаляет одну из приставок с начала строки (самую длинную подходящую)."""
    if not s or not isinstance(s, str):
        return s
    # Сортируем по длине убывание, чтобы сначала проверять длинные
    for p in sorted(prefixes, key=len, reverse=True):
        if not p:
            continue
        check = s.lower() if case_insensitive else s
        pre = p.lower() if case_insensitive else p
        if check.startswith(pre):
            return s[len(p) :].strip()
    return s.strip()


def strip_title_suffix(s: str) -> str:
    """Убирает » и ». в конце; убирает лишние » перед ( или пробелом в середине."""
    if not s:
        return s
    s = s.strip()
    if s.endswith("»."):
        s = s[:-2].strip()
    elif s.endswith("»"):
        s = s[:-1].strip()
    # Оставшиеся » перед скобкой или запятой (артефакты обёрток)
    s = s.replace("» (", " (").replace("», ", ", ")
    if s.endswith("»"):
        s = s[:-1].strip()
    return s


def clean_persons(lst: list) -> list:
    return [strip_prefix(x, PERSONS_PREFIXES) for x in lst if x]


def clean_organizations(lst: list) -> list:
    return [strip_prefix(x, ORGANIZATIONS_PREFIXES) for x in lst if x]


def clean_titles(lst: list) -> list:
    out = []
    for x in lst:
        if not x:
            continue
        x = strip_prefix(x, TITLES_PREFIXES)
        x = strip_title_suffix(x)
        if x:
            out.append(x)
    return out


def clean_urls(lst: list) -> list:
    return [strip_prefix(x, URLS_PREFIXES) for x in lst if x]


def clean_output(output_str: str) -> str:
    """Парсит output JSON, чистит значения, возвращает новую JSON-строку."""
    try:
        data = json.loads(output_str)
    except json.JSONDecodeError:
        return output_str
    if "persons" in data:
        data["persons"] = clean_persons(data["persons"])
    if "organizations" in data:
        data["organizations"] = clean_organizations(data["organizations"])
    if "titles" in data:
        data["titles"] = clean_titles(data["titles"])
    if "urls" in data:
        data["urls"] = clean_urls(data["urls"])
    return json.dumps(data, ensure_ascii=False)


def process_file(path: Path) -> int:
    """Читает JSONL, чистит output в каждой строке, перезаписывает файл. Возвращает число строк."""
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                lines.append(line)
                continue
            if "output" in rec:
                rec["output"] = clean_output(rec["output"])
            lines.append(json.dumps(rec, ensure_ascii=False))
    with open(path, "w", encoding="utf-8") as f:
        for ln in lines:
            f.write(ln + "\n")
    return len(lines)


def main():
    files = [
        BASE / "instruction_dataset_10k.jsonl",
        BASE / "instruction_dataset_100k.jsonl",
        BASE / "instruction_dataset_test.jsonl",
    ]
    for p in files:
        if not p.exists():
            print(f"Пропуск (нет файла): {p}")
            continue
        n = process_file(p)
        print(f"Обработано: {p.name} ({n} строк)")


if __name__ == "__main__":
    main()
