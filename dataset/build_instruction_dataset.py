# -*- coding: utf-8 -*-
"""
Генерация instruction-датасета для дообучения Llama на извлечение сущностей из текста.
- Классы: fio, organization, title, url (без other).
- Чанки по 4–5 предложений из курсовая.txt.
- Выход: JSON с полями persons, organizations, titles, urls.
- Цель: 100 000 примеров.
"""

import json
import re
import random
from pathlib import Path
from collections import defaultdict

# пути относительно скрипта
BASE = Path(__file__).resolve().parent
CSV_PATH = BASE / "drobimdataset" / "dataset_01_expanded_only_white.csv"
KURS_PATH = BASE / "курсовая.txt"
OUT_JSONL = BASE / "instruction_dataset_100k.jsonl"
OUT_JSONL_SMALL = BASE / "instruction_dataset_10k.jsonl"  # срез для проверки
OUT_TEST_JSONL = BASE / "instruction_dataset_test.jsonl"  # тест без пересечения с 100k

# Классы: fio, organization, title, url (без other — избыточно для Llama)
INSTRUCTION = "Извлеки сущности из текста и верни JSON с полями: persons, organizations, titles, urls. Только валидный JSON, без пояснений."

LABEL_KEYS = ("persons", "organizations", "titles", "urls")


# Максимальная длина организации в пуле (без составных "возглавляемая ... по адресу")
MAX_ORG_LENGTH = 120
# Подстроки, по которым отбрасываем составные организации из пула
ORG_COMPOSITE_MARKERS = (" возглавляемая ", " по адресу ", " расположенная в ", " в домовладении ", " заявитель ", " истец ", " ответчик ")


def load_csv_entities(csv_path: Path):
    """Загружает CSV; организации фильтруем — без длинных составных (организация + ФИО + адрес)."""
    import csv
    persons, organizations, titles, urls = [], [], [], []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or "").strip()
            label = (row.get("label") or "").strip().lower()
            if not text or not label or label == "other":
                continue
            if label == "fio":
                persons.append(text)
            elif label == "organization":
                if len(text) <= MAX_ORG_LENGTH and not any(m in text.lower() for m in ORG_COMPOSITE_MARKERS):
                    organizations.append(text)
                elif len(text) <= MAX_ORG_LENGTH:
                    # Берём только часть до первого составного маркера — чистое название
                    t_lower = text.lower()
                    cut = len(text)
                    for m in ORG_COMPOSITE_MARKERS:
                        idx = t_lower.find(m)
                        if idx != -1 and idx < cut:
                            cut = idx
                    clean = text[:cut].strip()
                    if len(clean) > 5 and clean not in organizations:
                        organizations.append(clean)
            elif label == "title":
                titles.append(text)
            elif label == "url":
                urls.append(text)
    return {
        "persons": persons,
        "organizations": organizations,
        "titles": titles,
        "urls": urls,
    }


def split_into_sentences(text: str):
    """Разбивает текст на предложения (по . ! ? и переносам)."""
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]


def build_chunks(kurs_path: Path, rng: random.Random, min_sent=4, max_sent=5):
    """Строит чанки по 4–5 предложений из файла курсовых."""
    with open(kurs_path, "r", encoding="utf-8") as f:
        raw = f.read()
    sentences = split_into_sentences(raw)
    chunks = []
    i = 0
    while i < len(sentences):
        n = rng.randint(min_sent, max_sent)
        block = sentences[i : i + n]
        if len(block) >= min_sent:
            chunk = " ".join(block)
            if len(chunk) > 100:
                chunks.append(chunk)
        i += n
    return chunks


def inject_entities(chunk: str, entities: dict, rng: random.Random) -> str:
    """Добавляет сущности в конец чанка естественными фразами."""
    parts = [chunk]
    added = []
    # ФИО
    for name in entities.get("persons", [])[:2]:
        if name not in added:
            parts.append(f"По мнению {name}, изложенному в работе, важны указанные выводы.")
            added.append(name)
    # Организации
    for org in entities.get("organizations", [])[:2]:
        if org not in added:
            parts.append(f"Согласно данным {org}, приведённым в отчёте, это подтверждается.")
            added.append(org)
    # Названия (книги/фильмы/песни — один класс title)
    for title in entities.get("titles", [])[:2]:
        parts.append(f"Упоминается произведение «{title[:100]}{'…' if len(title) > 100 else ''}».")
    # URL
    for url in entities.get("urls", [])[:2]:
        parts.append(f"Подробнее: {url}")
    return " ".join(parts)


def _truncate_composite_org(s: str) -> str:
    """Оставляет только название организации без «возглавляемая ...», «по адресу ...»."""
    t_lower = s.lower()
    cut = len(s)
    for m in ORG_COMPOSITE_MARKERS:
        idx = t_lower.find(m)
        if idx != -1 and idx < cut:
            cut = idx
    return s[:cut].strip().strip(".,")


def extract_entities_from_text(text: str) -> dict:
    """
    Извлекает сущности из полного текста (чанк + вставки), чтобы output не терял сущности.
    Возвращает {persons, organizations, titles, urls} — списки без дубликатов.
    """
    out = {k: [] for k in LABEL_KEYS}
    seen = {k: set() for k in LABEL_KEYS}

    # URL
    for m in re.findall(r"https?://[^\s\]\)\"\']+", text):
        m_clean = m.rstrip(".,;:")
        if m_clean not in seen["urls"] and len(m_clean) > 10:
            seen["urls"].add(m_clean)
            out["urls"].append(m_clean)

    # Организации: полная форма АО «СУЭК», ООО «...», МЕСТНАЯ РЕЛИГИОЗНАЯ ОРГАНИЗАЦИЯ ... (без хвоста "возглавляемая ...")
    org_patterns = [
        r"(?:АО|ООО|ПАО|ЗАО|ИП|НКО)\s*[«\"][^»\"]+[»\"]",
        r"МЕСТНАЯ РЕЛИГИОЗНАЯ ОРГАНИЗАЦИЯ[^.,]+?(?=\s*[.,]|\s+Согласно|\s+Упоминается|\s+Подробнее|$)",
        r"ФГБОУ[^.,]+?(?=\s*[.,]|\s+Согласно|$)",
        r"МГУ[^.,]*?(?=\s*[.,]|$)",
    ]
    for pattern in org_patterns:
        for m in re.findall(pattern, text, re.IGNORECASE):
            name = (m if isinstance(m, str) else m[0]).strip()
            name = _truncate_composite_org(name)
            if len(name) > 2 and name not in seen["organizations"]:
                seen["organizations"].add(name)
                out["organizations"].append(name)
    # Из шаблона "Согласно данным X, приведённым" — только короткое название (без составного хвоста)
    for m in re.findall(r"(?:согласно данным|договор с|контракт с|со стороны|в организации)\s+([^.,]+?)(?=\s*[.,]|\s+приведённым|$)", text, re.IGNORECASE):
        name = m.strip()
        name = _truncate_composite_org(name)
        if len(name) > 2 and len(name) <= MAX_ORG_LENGTH and name not in seen["organizations"]:
            seen["organizations"].add(name)
            out["organizations"].append(name)

    # Persons: "По мнению X, изложенному" и ФИО (И.И. Фамилия, Фамилия И.О., Б.Л. Пастернак)
    for m in re.findall(r"По мнению\s+([^,]+?),\s*изложенному", text):
        name = m.strip()
        if len(name) > 3 and name not in seen["persons"]:
            seen["persons"].add(name)
            out["persons"].append(name)
    _skip_person_start = {"организация", "группа", "компания", "религиозная", "местная", "суд", "сторона", "данные", "мнение", "произведение", "договор", "контракт"}
    for m in re.findall(r"\b([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.[А-ЯЁ]\.?|\s+[А-ЯЁ]\.))\b", text):
        name = m.strip()
        if name.split()[0].lower() in _skip_person_start or len(name) < 5 or name in seen["persons"]:
            continue
        seen["persons"].add(name)
        out["persons"].append(name)
    for m in re.findall(r"\b([А-ЯЁ]\.[А-ЯЁ]\.?\s*[А-ЯЁ][а-яё]+)\b", text):
        name = m.strip()
        if len(name) > 3 and name not in seen["persons"]:
            seen["persons"].add(name)
            out["persons"].append(name)

    # Titles: "Упоминается произведение «...»"
    for m in re.findall(r"Упоминается произведение\s*[«\"]([^»\"]+)[»\"]", text):
        t = m.strip()
        if len(t) > 1 and t not in seen["titles"]:
            seen["titles"].add(t)
            out["titles"].append(t)

    return out


def merge_entities(extracted: dict, injected: dict) -> dict:
    """Объединяет извлечённые из текста и инжектированные сущности, без дубликатов."""
    merged = {}
    for k in LABEL_KEYS:
        seen = set()
        result = []
        for src in (extracted.get(k, []), injected.get(k, [])):
            for x in src:
                x = (x or "").strip()
                if not x:
                    continue
                key = x.lower()
                if key not in seen:
                    seen.add(key)
                    result.append(x)
        merged[k] = result
    return merged


def build_output_json(entities: dict) -> str:
    """Формирует строку JSON для output. Классы: persons, organizations, titles, urls."""
    out = {k: list(entities.get(k, [])) for k in LABEL_KEYS}
    return json.dumps(out, ensure_ascii=False)


def sample_entities_for_example(entity_pools: dict, rng: random.Random):
    """Выбирает случайный набор сущностей для одного примера (комбинации 0–2 на категорию)."""
    chosen = defaultdict(list)
    for key in LABEL_KEYS:
        pool = entity_pools.get(key) or []
        if not pool:
            continue
        n = rng.randint(0, 2)
        for _ in range(n):
            chosen[key].append(rng.choice(pool))
    return dict(chosen)


def main():
    seed = 42
    rng = random.Random(seed)
    target_count = 100_000
    check_count = 10_000  # срез для проверки (instruction_dataset_10k.jsonl)

    print("Загрузка сущностей из CSV (классы: fio, organization, title, url)...")
    entity_pools = load_csv_entities(CSV_PATH)
    for k, v in entity_pools.items():
        print(f"  {k}: {len(v)}")

    print("Построение чанков из курсовая.txt...")
    chunks = build_chunks(KURS_PATH, rng, min_sent=4, max_sent=5)
    print(f"  Чанков: {len(chunks)}")
    if len(chunks) < 1000:
        while len(chunks) < 40000:
            chunks.extend(chunks[:5000])
        rng.shuffle(chunks)

    # Генерация 100k примеров: output = полная разметка (извлечённые из текста + инжектированные)
    examples = []
    for i in range(target_count):
        chunk = rng.choice(chunks)
        entities = sample_entities_for_example(entity_pools, rng)
        if rng.random() < 0.12:
            entities = {k: [] for k in LABEL_KEYS}
        input_text = inject_entities(chunk, entities, rng)
        extracted = extract_entities_from_text(input_text)
        merged = merge_entities(extracted, entities)
        output_str = build_output_json(merged)
        examples.append({
            "instruction": INSTRUCTION,
            "input": input_text,
            "output": output_str,
        })
        if (i + 1) % 10000 == 0:
            print(f"  сгенерировано {i + 1}")

    # Сохранение 100k (обучающая выборка)
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"Сохранено {len(examples)} примеров в {OUT_JSONL}")

    # Множество input обучающей выборки — для непересекающегося теста
    train_inputs = {ex["input"] for ex in examples}

    # Срез 10k для проверки (из тех же 100k)
    small = examples[:check_count]
    with open(OUT_JSONL_SMALL, "w", encoding="utf-8") as f:
        for ex in small:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"Сохранено {len(small)} примеров в {OUT_JSONL_SMALL}")

    # Тестовый датасет: примеры с другими комбинациями (другой seed), без пересечения по input
    test_count = 10_000
    test_seed = 999
    rng_test = random.Random(test_seed)
    # Чанки для теста — те же, но порядок выбора другой из-за другого seed
    chunks_test = build_chunks(KURS_PATH, rng_test, min_sent=4, max_sent=5)
    if len(chunks_test) < 1000:
        while len(chunks_test) < 40000:
            chunks_test.extend(chunks_test[:5000])
        rng_test.shuffle(chunks_test)

    test_examples = []
    test_inputs_seen = set()
    attempts = 0
    max_attempts = test_count * 20
    print(f"\nГенерация тестового датасета {test_count} примеров (без пересечения с 100k)...")
    while len(test_examples) < test_count and attempts < max_attempts:
        chunk = rng_test.choice(chunks_test)
        entities = sample_entities_for_example(entity_pools, rng_test)
        if rng_test.random() < 0.12:
            entities = {k: [] for k in LABEL_KEYS}
        input_text = inject_entities(chunk, entities, rng_test)
        if input_text in train_inputs or input_text in test_inputs_seen:
            attempts += 1
            continue
        test_inputs_seen.add(input_text)
        extracted = extract_entities_from_text(input_text)
        merged = merge_entities(extracted, entities)
        output_str = build_output_json(merged)
        test_examples.append({
            "instruction": INSTRUCTION,
            "input": input_text,
            "output": output_str,
        })
        if len(test_examples) % 2000 == 0 and len(test_examples) > 0:
            print(f"  тест: {len(test_examples)}")
        attempts = 0
    if len(test_examples) < test_count:
        print(f"  предупреждение: сгенерировано {len(test_examples)} тестовых (цель {test_count})")
    with open(OUT_TEST_JSONL, "w", encoding="utf-8") as f:
        for ex in test_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"Сохранено {len(test_examples)} тестовых примеров в {OUT_TEST_JSONL} (не пересекаются с 100k)")

    print("\nПример первой записи (train):")
    print(json.dumps(examples[0], ensure_ascii=False, indent=2)[:900] + "...")


if __name__ == "__main__":
    main()
