# -*- coding: utf-8 -*-
"""
Дополнение датасета из внешних файлов:
- фио.txt: формат "N | ФИО | DD.MM.YYYY | город" → вычленить ФИО, аугментировать → 10k
- орг.txt: названия организаций по строке → аугментировать → 10k
- книги.txt: названия книг/песен по строке → аугментировать → 10k
- ссылки.txt: ссылки по строке → аугментировать → 10k
"""

import csv
import re
import random
from pathlib import Path

random.seed(123)
# Корень проекта DIPLOM (родитель папки dataset)
BASE = Path(__file__).resolve().parent.parent
if not (BASE / "фио.txt").exists() and (Path.cwd().parent / "фио.txt").exists():
    BASE = Path.cwd().parent

# --- ФИО из фио.txt ---
def parse_fio_line(line):
    """Строка: "500 | Платонов Илья Викторович | 06.05.1994 | Ковылкино" -> (Фамилия, Имя, Отчество)."""
    line = line.strip()
    if not line:
        return None
    # Извлекаем три подряд идущих слова (кириллица, возможен дефис): Фамилия Имя Отчество
    m = re.search(r"([А-Яа-яёЁ][а-яёА-Я\-]*)\s+([А-Яа-яёЁ][а-яёА-Я\-]*)\s+([А-Яа-яёЁ][а-яёА-Я\-]+)", line)
    if m:
        return (m.group(1), m.group(2), m.group(3))
    # Два слова: Фамилия Имя
    m2 = re.search(r"([А-Яа-яёЁ][а-яёА-Я\-]+)\s+([А-Яа-яёЁ][а-яёА-Я\-]+)", line)
    if m2:
        return (m2.group(1), m2.group(2), "")
    return None

def augment_fio(surname, name, patronymic):
    """Генерирует разные формы одного ФИО. patronymic может быть пустым."""
    forms = []
    full = f"{surname} {name} {patronymic}".strip()
    forms.append(full)
    if patronymic:
        forms.append(f"{name} {patronymic} {surname}")
        forms.append(f"{surname} {name[0]}.{patronymic[0]}.")
        forms.append(f"{name[0]}.{patronymic[0]}. {surname}")
        forms.append(f"{surname} {name[0]}. {patronymic}")
    forms.append(f"{name} {surname}")
    forms.append(f"{surname} {name}")
    forms.append(f"{name[0]}. {surname}")
    if not patronymic:
        forms.append(f"{surname} {name[0]}.")
    return forms

# Резервный список ФИО (если файл недоступен при запуске)
FIO_FALLBACK = [
    ("Иванов", "Сергей", "Петрович"), ("Петров", "Алексей", "Владимирович"), ("Сидоров", "Михаил", "Андреевич"),
    ("Кузнецов", "Дмитрий", "Олегович"), ("Смирнов", "Антон", "Игоревич"), ("Волков", "Роман", "Сергеевич"),
    ("Федоров", "Денис", "Николаевич"), ("Морозов", "Павел", "Евгеньевич"), ("Новиков", "Артем", "Викторович"),
    ("Орлов", "Илья", "Максимович"), ("Васильев", "Кирилл", "Александрович"), ("Зайцев", "Егор", "Сергеевич"),
    ("Павлов", "Никита", "Олегович"), ("Семенов", "Тимофей", "Ильич"), ("Николаев", "Арсений", "Романович"),
    ("Макаров", "Владимир", "Петрович"), ("Захаров", "Максим", "Денисович"), ("Борисов", "Олег", "Юрьевич"),
    ("Киселев", "Андрей", "Михайлович"), ("Григорьев", "Степан", "Алексеевич"), ("Егоров", "Даниил", "Константинович"),
    ("Комаров", "Вячеслав", "Игоревич"), ("Лебедев", "Александр", "Сергеевич"), ("Соловьев", "Роман", "Евгеньевич"),
    ("Тихонов", "Илья", "Павлович"), ("Крылов", "Матвей", "Денисович"), ("Романов", "Петр", "Николаевич"),
    ("Алексеев", "Владислав", "Игоревич"), ("Демидов", "Никита", "Олегович"), ("Антонов", "Евгений", "Сергеевич"),
    ("Миронов", "Артур", "Владимирович"), ("Фролов", "Денис", "Петрович"), ("Белов", "Тимур", "Александрович"),
    ("Королев", "Артем", "Сергеевич"), ("Жуков", "Роман", "Олегович"), ("Шестаков", "Никита", "Дмитриевич"),
    ("Калинин", "Максим", "Юрьевич"), ("Котов", "Илья", "Анатольевич"), ("Осипов", "Владислав", "Сергеевич"),
    ("Ларионов", "Алексей", "Павлович"), ("Мельников", "Даниил", "Игоревич"), ("Сафонов", "Роман", "Константинович"),
    ("Ефимов", "Артем", "Николаевич"), ("Гусев", "Тимофей", "Владимирович"), ("Капустин", "Денис", "Сергеевич"),
    ("Широков", "Матвей", "Олегович"), ("Прохоров", "Никита", "Андреевич"), ("Рябов", "Илья", "Сергеевич"),
    ("Нестеров", "Михаил", "Петрович"), ("Фомин", "Арсений", "Игоревич"), ("Беляев", "Роман", "Евгеньевич"),
    ("Трофимов", "Владислав", "Сергеевич"), ("Зорин", "Кирилл", "Алексеевич"), ("Панкратов", "Илья", "Дмитриевич"),
    ("Логинов", "Денис", "Олегович"), ("Савельев", "Максим", "Юрьевич"), ("Коновалов", "Артем", "Сергеевич"),
    ("Руднев", "Павел", "Андреевич"), ("Князев", "Никита", "Михайлович"), ("Пахомов", "Дмитрий", "Игоревич"),
    ("Данилов", "Алексей", "Петрович"), ("Яковлев", "Артур", "Сергеевич"), ("Федосеев", "Тимур", "Олегович"),
    ("Карпов", "Максим", "Владимирович"), ("Лыткин", "Роман", "Игоревич"), ("Суханов", "Денис", "Николаевич"),
    ("Минин", "Илья", "Сергеевич"), ("Чернов", "Арсений", "Олегович"), ("Астахов", "Владислав", "Петрович"),
    ("Куликов", "Матвей", "Юрьевич"), ("Ершов", "Никита", "Денисович"), ("Гордеев", "Роман", "Алексеевич"),
    ("Платонов", "Артем", "Сергеевич"), ("Баранов", "Илья", "Олегович"), ("Кожевников", "Денис", "Владимирович"),
    ("Абрамов", "Тимофей", "Сергеевич"), ("Селезнев", "Максим", "Игоревич"), ("Тарасов", "Арсений", "Дмитриевич"),
    ("Лосев", "Владислав", "Сергеевич"), ("Костин", "Роман", "Николаевич"), ("Хасанов", "Руслан", "Маратович"),
    ("Платонов", "Илья", "Викторович"), ("Фёдоров", "Илья", "Викторович"), ("Волков", "Алексей", "Сергеевич"),
    ("Борисов", "Роман", "Викторович"), ("Киселёв", "Денис", "Петрович"), ("Морозов", "Илья", "Сергеевич"),
    ("Николаев", "Артём", "Викторович"), ("Павлов", "Денис", "Сергеевич"), ("Соколов", "Илья", "Петрович"),
    ("Семёнов", "Алексей", "Викторович"), ("Григорьев", "Денис", "Петрович"), ("Ларионов", "Роман", "Сергеевич"),
]

def _find_fio_file():
    """Ищем фио.txt в корне проекта."""
    for p in [BASE / "фио.txt", Path.cwd() / "фио.txt", Path.cwd().parent / "фио.txt", BASE.parent / "фио.txt"]:
        if p.exists() and p.stat().st_size > 0:
            return p
    for d in [BASE, Path.cwd(), Path.cwd().parent]:
        if d.exists():
            for f in d.iterdir():
                if f.is_file() and f.suffix.lower() == ".txt" and ("fio" in f.name.lower() or "фио" in f.name.lower()) and f.stat().st_size > 0:
                    return f
    return None

def load_and_augment_fio(target=10000):
    base_fios = []
    path = _find_fio_file()
    if path:
        for enc in ("utf-8-sig", "utf-8", "cp1251"):
            try:
                with open(path, "r", encoding=enc) as f:
                    raw = f.read()
                for line in raw.splitlines():
                    parsed = parse_fio_line(line)
                    if parsed:
                        base_fios.append(parsed)
                if base_fios:
                    break
            except Exception:
                continue
    if not base_fios:
        base_fios = list(FIO_FALLBACK)  # резервный список
    seen = set()
    result = []
    prefixes = ["", "от ", "для ", "на имя ", "документ на ", "выдано "]
    # Сначала все формы из всех ФИО
    for s, n, p in base_fios:
        for form in augment_fio(s, n, p):
            if form not in seen:
                seen.add(form)
                result.append(form)
    # Добиваем префиксами
    base_clean = [r for r in result if not any(r.startswith(x) for x in ["от ", "для ", "на имя ", "документ ", "выдано "])]
    for _ in range(target * 3):
        if len(result) >= target:
            break
        base = random.choice(base_clean)
        pref = random.choice(prefixes)
        if pref:
            candidate = pref + base
            if candidate not in seen:
                seen.add(candidate)
                result.append(candidate)
    # Если всё ещё не хватает — комбинируем фамилию из одного, имя из другого
    if len(result) < target and base_fios:
        names = list(set(n for _, n, _ in base_fios))
        patronymics = list(set(p for _, _, p in base_fios if p))
        for s, _, _ in base_fios:
            for _ in range(20):
                if len(result) >= target:
                    break
                n, p = random.choice(names), (random.choice(patronymics) if patronymics else "")
                for form in augment_fio(s, n, p):
                    if form not in seen:
                        seen.add(form)
                        result.append(form)
                        if len(result) >= target:
                            break
    return result[:target]


# --- Организации из орг.txt ---
def load_and_augment_orgs(target=10000):
    path = BASE / "орг.txt"
    if not path.exists():
        raise FileNotFoundError(path)
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
    if not lines:
        return []
    prefixes = ["", "в ", "из ", "для ", "согласно договору с ", "контракт с ", "в организации ", "сотрудник ",
                "от ", "направлено в ", "договор с ", "в адрес ", "получено от ", "в лице ", "со стороны ",
                "подразделение ", "в структуре ", "учёт в ", "лицензия "]
    seen = set()
    result = []
    for org in lines:
        for pref in prefixes:
            text = (pref + org).strip() if pref else org
            if text not in seen:
                seen.add(text)
                result.append(text)
    random.shuffle(result)
    if len(result) < target:
        # Добиваем повторным сочетанием org + префикс в другом порядке
        for _ in range(target - len(result)):
            org = random.choice(lines)
            text = random.choice(prefixes) + org
            if text not in seen:
                seen.add(text)
                result.append(text)
    return result[:target]


# --- Книги/песни из книги.txt ---
def parse_book_line(line):
    """Извлечь название и опционально автора. Форматы: Автор "Название", Автор — "Название", «Название» — Автор и т.д."""
    line = line.strip()
    if not line:
        return None, None
    # Ищем кавычки « » или " "
    title = None
    author = None
    for q1, q2 in [('"', '"'), ('«', '»'), ("'", "'")]:
        i = line.find(q1)
        if i != -1:
            j = line.find(q2, i + 1)
            if j != -1:
                title = line[i + 1:j].strip()
                before = line[:i].strip()
                after = line[j + 1:].strip()
                # Убрать "Автор:", "Исполнитель:", "Песня:", " — "
                for sep in [" — ", " – ", " | ", ": ", " (исп. ", " ("]:
                    if sep in before:
                        author = before.split(sep)[0].strip()
                        break
                    if sep in after:
                        author = after.split(sep)[-1].strip().rstrip(")")
                        break
                if not author and before:
                    author = before.rstrip(":")
                break
    if not title:
        # Без кавычек: "Ночь love — Мумий Тролль" или "Автор: X | Песня: Y"
        if " | " in line:
            for part in line.split("|"):
                if "Песня:" in part or "Название:" in part or "песня:" in part:
                    title = part.split(":", 1)[-1].strip()
                    break
                if "Автор:" in part:
                    author = part.split(":", 1)[-1].strip()
            if not title:
                title = line
        else:
            title = line
    return (title or line).strip(), (author or "").strip()

def load_and_augment_titles(target=10000):
    path = BASE / "книги.txt"
    if not path.exists():
        raise FileNotFoundError(path)
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            title, author = parse_book_line(line)
            if title:
                entries.append((title, author))
    if not entries:
        return []
    seen = set()
    result = []
    wrappers = [
        lambda t, a: t,
        lambda t, a: f"«{t}»",
        lambda t, a: f'"{t}"',
        lambda t, a: f"Книга «{t}»",
        lambda t, a: f"Песня «{t}»",
        lambda t, a: f"Фильм «{t}»",
        lambda t, a: f"Роман «{t}»",
    ]
    with_author = [
        lambda t, a: f"{t} (автор: {a})" if a else t,
        lambda t, a: f"«{t}» — {a}" if a else f"«{t}»",
        lambda t, a: f"«{t}», {a}" if a else f"«{t}»",
    ]
    pool = []
    for title, author in entries:
        for wrap in wrappers:
            text = wrap(title, author)
            if text and text not in seen:
                seen.add(text)
                pool.append(text)
        if author:
            for wa in with_author:
                text = wa(title, author)
                if text and text not in seen:
                    seen.add(text)
                    pool.append(text)
    for _ in range(len(entries)):
        t = random.choice(pool)
        t2 = t + random.choice([" — роман", " — повесть", " — песня", f" ({random.randint(1950, 2024)})"])
        if t2 not in seen:
            seen.add(t2)
            pool.append(t2)
    random.shuffle(pool)
    result = pool[:target]
    while len(result) < target:
        base = random.choice(result)
        candidate = base + f" ({random.randint(1950, 2024)})"
        if candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return result[:target]


# --- Ссылки из ссылки.txt ---
def load_and_augment_urls(target=10000):
    path = BASE / "ссылки.txt"
    if not path.exists():
        raise FileNotFoundError(path)
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and (line.startswith("http://") or line.startswith("https://")):
                lines.append(line)
    if not lines:
        return []
    path_suffixes = ["", "/news", "/article", "/page", "/search", "/doc", "/about", "/contacts", "/faq", "/support", "/ru", "/en"]
    query_params = ["?page=1", "?ref=main", "?utm_source=link", "?id=1", "?q=test", "&sort=date", "&lang=ru"]
    seen = set()
    result = []
    for url in lines:
        base = url.rstrip("/")
        if base not in seen:
            seen.add(base)
            result.append(base)
        for path_suf in path_suffixes:
            if not path_suf:
                continue
            u = base + path_suf
            if u not in seen:
                seen.add(u)
                result.append(u)
            if len(result) >= target:
                break
        if len(result) >= target:
            break
    for url in lines:
        if len(result) >= target:
            break
        base = url.rstrip("/")
        for q in query_params:
            u = base + ("&" + q.lstrip("?&") if "?" in base else q)
            if u not in seen:
                seen.add(u)
                result.append(u)
    random.shuffle(result)
    return result[:target]


def main():
    out_path = BASE / "dataset" / "dataset_01_addition.csv"
    merged_path = BASE / "dataset" / "dataset_01_expanded.csv"

    print("Загрузка и аугментация ФИО из фио.txt...")
    fios = load_and_augment_fio(10000)
    print("Загрузка и аугментация организаций из орг.txt...")
    orgs = load_and_augment_orgs(10000)
    print("Загрузка и аугментация названий из книги.txt...")
    titles = load_and_augment_titles(10000)
    print("Загрузка и аугментация ссылок из ссылки.txt...")
    urls = load_and_augment_urls(10000)

    rows = []
    for t in fios:
        rows.append((t, "fio"))
    for t in orgs:
        rows.append((t, "organization"))
    for t in titles:
        rows.append((t, "title"))
    for t in urls:
        rows.append((t, "url"))

    random.shuffle(rows)

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["text", "label"])
        for text, label in rows:
            w.writerow([text, label])

    from collections import Counter
    cnt = Counter(label for _, label in rows)
    print(f"Записано дополнение: {len(rows)} строк в {out_path}")
    print("По классам:", dict(cnt))

    # Слияние с основным датасетом: передайте аргумент --merge
    if len(__import__("sys").argv) > 1 and __import__("sys").argv[1] == "--merge" and merged_path.exists():
        with open(merged_path, "r", encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
        with open(merged_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["text", "label"])
            w.writeheader()
            w.writerows(existing)
            for text, label in rows:
                w.writerow({"text": text, "label": label})
        print(f"Дополнение добавлено к {merged_path}. Всего строк: {len(existing) + len(rows)}")


if __name__ == "__main__":
    main()
