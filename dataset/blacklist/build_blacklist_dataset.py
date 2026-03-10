# -*- coding: utf-8 -*-
"""
Сбор датасета blacklist.csv (столбцы text, label) из CSV в папке blacklist.
По 30 000 примеров каждого класса; при нехватке — аугментация.

fio:          parser1_data_физические_лица.csv — столбец 2 (ФИО)
organization: parser1_data_организации.csv — столбец 2 (наименование)
              parser2_data.csv — столбец 7 (Наименование организации)
              parser3_data.csv — столбец 2
              parser4_data.csv — столбец 2
title:        parser7_exportfsm.csv — столбец 2 (Материал)
url:          rknweb_blocked_sites.csv — столбец 3 (домен/URL)
"""

import csv
import random
import re
from pathlib import Path

random.seed(42)
TARGET = 30_000
BASE = Path(__file__).resolve().parent


def read_csv_column(path, col_1based, encoding="utf-8", delimiter=",", skip_empty=True, skip_lines=1):
    """Читает один столбец из CSV (col_1based: 1 = первый столбец). skip_lines — сколько строк заголовка пропустить."""
    col_idx = col_1based - 1
    values = []
    try:
        with open(path, "r", encoding=encoding, newline="", errors="replace") as f:
            r = csv.reader(f, delimiter=delimiter)
            for _ in range(skip_lines):
                next(r, None)
            for row in r:
                if col_idx < len(row):
                    v = row[col_idx].strip()
                    if skip_empty and not v:
                        continue
                    values.append(v)
    except Exception as e:
        print(f"  Ошибка чтения {path.name}: {e}")
    return values


def normalize_text(s):
    if not s:
        return ""
    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


# --- FIO ---
def load_fio():
    path = BASE / "parser1_data_физические_лица.csv"
    if not path.exists():
        return []
    raw = read_csv_column(path, 2)
    return list(dict.fromkeys(normalize_text(v) for v in raw if normalize_text(v)))


def augment_fio(items, target):
    """Аугментация ФИО: разные формы (Фамилия И.О., И.О. Фамилия и т.д.)."""
    seen = set(items)
    result = list(items)
    for full in items:
        if len(result) >= target:
            break
        parts = full.split()
        if len(parts) >= 3:
            s, n, p = parts[0], parts[1], parts[2]
            for form in [
                f"{s} {n[0]}.{p[0]}.",
                f"{n[0]}.{p[0]}. {s}",
                f"{n} {s}",
                f"{s} {n}",
            ]:
                if form not in seen:
                    seen.add(form)
                    result.append(form)
                    if len(result) >= target:
                        break
    while len(result) < target:
        base = random.choice(items)
        parts = base.split()
        if len(parts) >= 3:
            form = f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
            if form not in seen:
                seen.add(form)
                result.append(form)
        if len(result) >= target:
            break
    return result[:target]


# --- Organization ---
def load_organization():
    out = []
    # (файл, столбец_1based, skip_lines). parser5_data.csv пока не используем (смешаны ФИО и организации)
    for name, col, skip in [
        ("parser1_data_организации.csv", 2, 1),
        ("parser2_data.csv", 7, 1),
        ("parser3_data.csv", 2, 1),
        ("parser4_data.csv", 2, 2),  # два заголовка
    ]:
        path = BASE / name
        if path.exists():
            out.extend(read_csv_column(path, col, skip_lines=skip))
    return list(dict.fromkeys(normalize_text(v) for v in out if normalize_text(v)))


def augment_organization(items, target):
    prefixes = [
        "", "в ", "из ", "для ", "ООО ", "АО ", "организация ", "в лице ", "договор с ",
        "согласно реестру ", "в перечень ", "исключить из перечня ", "наименование: ",
        "учредитель ", "ответчик ", "истец ", "заявитель ", "сторона по делу ",
    ]
    seen = set(items)
    result = list(items)
    for _ in range(target * 4):
        if len(result) >= target:
            break
        base = random.choice(items)
        pref = random.choice(prefixes)
        text = (pref + base).strip() if pref else base
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result[:target]


# --- Title ---
def load_title():
    path = BASE / "parser7_exportfsm.csv"
    if not path.exists():
        return []
    raw = read_csv_column(path, 2, delimiter=";")
    return list(dict.fromkeys(normalize_text(v) for v in raw if normalize_text(v)))


def augment_title(items, target):
    wrappers = [
        lambda t: t,
        lambda t: f"«{t[:80]}»" if len(t) > 80 else f"«{t}»",
        lambda t: f"Книга «{t[:60]}»" if len(t) > 60 else f"Книга «{t}»",
        lambda t: f"Фильм «{t[:60]}»" if len(t) > 60 else f"Фильм «{t}»",
        lambda t: f"Материал «{t[:60]}»" if len(t) > 60 else f"Материал «{t}»",
    ]
    suffix_templates = ["", " — запрещён", " (в перечне)", " ({} г.)", " — издание"]
    seen = set(items)
    result = list(items)
    for _ in range(target * 3):
        if len(result) >= target:
            break
        base = random.choice(items)
        text = random.choice(wrappers)(base)
        if random.random() < 0.3:
            suf = random.choice(suffix_templates)
            if suf:
                text = text + (suf.format(random.randint(1990, 2024)) if "{}" in suf else suf)
        if text not in seen:
            seen.add(text)
            result.append(text)
    while len(result) < target:
        base = random.choice(items)
        text = base + f" ({random.randint(1990, 2024)})"
        if text not in seen:
            seen.add(text)
            result.append(text)
        if len(result) >= target:
            break
    return result[:target]


# --- URL ---
def load_url():
    path = BASE / "rknweb_blocked_sites.csv"
    if not path.exists():
        return []
    raw = read_csv_column(path, 3)
    result = []
    seen = set()
    for v in raw:
        v = normalize_text(v)
        if not v or v in seen:
            continue
        # домен может быть без схемы — добавляем https://
        if not v.startswith("http"):
            v = "https://" + v
        seen.add(v)
        result.append(v)
    return result


def main():
    out_path = BASE / "blacklist.csv"
    rows = []

    # FIO
    print("Загрузка ФИО...")
    fio_raw = load_fio()
    print(f"  Загружено {len(fio_raw)} уникальных ФИО")
    fio_list = augment_fio(fio_raw, TARGET) if len(fio_raw) < TARGET else fio_raw[:TARGET]
    for t in fio_list:
        rows.append((t, "fio"))
    print(f"  Итого fio: {len(fio_list)}")

    # Organization
    print("Загрузка организаций...")
    org_raw = load_organization()
    print(f"  Загружено {len(org_raw)} уникальных наименований")
    org_list = augment_organization(org_raw, TARGET) if len(org_raw) < TARGET else org_raw[:TARGET]
    for t in org_list:
        rows.append((t, "organization"))
    print(f"  Итого organization: {len(org_list)}")

    # Title
    print("Загрузка названий (title)...")
    title_raw = load_title()
    print(f"  Загружено {len(title_raw)} уникальных")
    title_list = augment_title(title_raw, TARGET) if len(title_raw) < TARGET else title_raw[:TARGET]
    for t in title_list:
        rows.append((t, "title"))
    print(f"  Итого title: {len(title_list)}")

    # URL
    print("Загрузка URL...")
    url_raw = load_url()
    print(f"  Загружено {len(url_raw)} уникальных URL")
    url_list = url_raw[:TARGET] if len(url_raw) >= TARGET else url_raw + random.choices(url_raw, k=TARGET - len(url_raw))
    if len(url_list) > TARGET:
        url_list = url_list[:TARGET]
    for t in url_list:
        rows.append((t, "url"))
    print(f"  Итого url: {len(url_list)}")

    random.shuffle(rows)

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["text", "label"])
        for text, label in rows:
            w.writerow([text, label])

    from collections import Counter
    c = Counter(r[1] for r in rows)
    print(f"\nЗаписано {len(rows)} строк в {out_path}")
    print("По классам:", dict(c))


if __name__ == "__main__":
    main()
