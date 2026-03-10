# -*- coding: utf-8 -*-
"""
Добавляет класс "other" (ни к одному классу не относится) в существующий dataset_01_expanded.csv.
Запуск: python add_other_class.py [количество]   (по умолчанию 20000)
"""
import csv
import random
import sys
from pathlib import Path

Path(__file__).resolve().parent
random.seed(42)

OTHER_PHRASES = [
    "привет", "спасибо", "до свидания", "не указано", "см. приложение", "дата выдачи", "дата подписания",
    "договор подписан", "вступил в силу", "без комментариев", "не применимо", "не требуется",
    "по запросу", "в соответствии с", "на основании", "в связи с", "в течение", "в целях",
    "и так далее", "и другие", "и т.д.", "и т.п.", "и прочее", "и аналогичные",
    "да", "нет", "не знаю", "возможно", "вероятно", "конечно", "разумеется",
    "первый", "второй", "третий", "последний", "следующий", "предыдущий",
    "сегодня", "вчера", "завтра", "утром", "вечером", "позже", "ранее",
    "здесь", "там", "везде", "нигде", "иногда", "всегда", "никогда",
    "очень", "слишком", "довольно", "совсем", "почти", "примерно", "около",
    "документ", "копия", "оригинал", "приложение", "выписка", "справка",
    "страница", "пункт", "раздел", "глава", "часть", "параграф",
    "сумма", "количество", "итого", "всего", "остаток", "процент",
    "подпись", "печать", "штамп", "дата", "номер", "исх.",
    "входящий", "исходящий", "исх. №", "на №", "на имя",
    "без изменений", "без замечаний", "принято", "отклонено", "на рассмотрении",
    "черновик", "оригинал документа", "заверенная копия", "лист",
]
OTHER_TEMPLATES = [
    "{} руб.", "{} шт.", "{} %", "№ {}", "п. {}", "стр. {}", "г. {}",
    "с {} по {}", "в период {} — {}", "не ранее {}", "не позднее {}",
    "{} (при наличии)", "{} при необходимости", "{} по согласованию",
]


def gen_other(count):
    seen = set()
    result = []
    numbers = [str(random.randint(1, 9999)) for _ in range(500)]
    for _ in range(count):
        if random.random() < 0.6:
            text = random.choice(OTHER_PHRASES)
        elif random.random() < 0.5:
            text = random.choice(OTHER_TEMPLATES).format(random.choice(numbers))
        else:
            text = " ".join(random.choices(OTHER_PHRASES, k=random.randint(2, 4)))
        if text not in seen:
            seen.add(text)
            result.append(text)
    while len(result) < count:
        text = random.choice(OTHER_PHRASES) + " " + random.choice(OTHER_PHRASES)
        if random.random() < 0.3:
            text += " " + str(random.randint(1, 999))
        if text not in seen:
            seen.add(text)
            result.append(text)
        if len(result) >= count:
            break
    return result[:count]


def main():
    base = Path(__file__).resolve().parent
    csv_path = base / "dataset_01_expanded.csv"
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000

    if not csv_path.exists():
        print(f"Файл не найден: {csv_path}")
        return

    print(f"Генерация {n} примеров класса 'other'...")
    other_rows = [(t, "other") for t in gen_other(n)]

    with open(csv_path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        existing = list(r)
        fieldnames = r.fieldnames

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(existing)
        for text, label in other_rows:
            w.writerow({"text": text, "label": label})

    print(f"Добавлено {n} строк с меткой 'other'. Всего строк в файле: {len(existing) + n}")


if __name__ == "__main__":
    main()
