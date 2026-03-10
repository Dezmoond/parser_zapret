# -*- coding: utf-8 -*-
"""
Удаляет дубликаты в списках output (persons, organizations, titles, urls) в JSONL.
Сохраняет порядок первого появления. Изменяет файлы на месте.
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
FILES = [
    BASE / "instruction_dataset_100k.jsonl",
    BASE / "instruction_dataset_10k.jsonl",
    BASE / "instruction_dataset_test.jsonl",
]
KEYS = ("persons", "organizations", "titles", "urls")


def dedup_list(lst):
    """Убирает дубликаты с сохранением порядка (сравнение без учёта регистра)."""
    seen = set()
    out = []
    for x in lst:
        if not isinstance(x, str):
            x = str(x)
        key = x.lower().strip()
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out


def process_line(line: str) -> str:
    rec = json.loads(line)
    out_str = rec.get("output")
    if not out_str:
        return line
    try:
        data = json.loads(out_str)
    except json.JSONDecodeError:
        return line
    for k in KEYS:
        if k in data and isinstance(data[k], list):
            data[k] = dedup_list(data[k])
    rec["output"] = json.dumps(data, ensure_ascii=False)
    return json.dumps(rec, ensure_ascii=False) + "\n"


def process_file(path: Path) -> tuple[int, int]:
    """Обрабатывает файл, перезаписывает. Возвращает (всего строк, строк с изменениями)."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = []
    changed = 0
    for line in lines:
        line = line.rstrip("\n")
        if not line.strip():
            new_lines.append(line + "\n" if line else "\n")
            continue
        new_line = process_line(line)
        if new_line.rstrip() != line:
            changed += 1
        new_lines.append(new_line if new_line.endswith("\n") else new_line + "\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return len(lines), changed


def main():
    for path in FILES:
        if not path.exists():
            print(f"Пропуск (нет файла): {path.name}")
            continue
        total, changed = process_file(path)
        print(f"{path.name}: строк {total}, изменено {changed}")


if __name__ == "__main__":
    main()
