# -*- coding: utf-8 -*-
"""
Добавляет в датасеты ~30 примеров с упоминанием запрещённых платформ:
facebook, фейсбук, meta, instagram, whatsapp, инстаграм, вотсап.
- extremism_detection_dataset_number_char: с полями start_char, end_char.
- extremism_detection_dataset: без меток (extremist_phrases — список строк).
Запуск из корня проекта: python extremism_detection_dataset_number_char/add_forbidden_platforms_examples.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTRUCTION = "Определи экстремизм в тексте. Ответ — JSON: found_extremism, extremist_phrases, categories."
CATEGORY = "запрещённые платформы"

# (input_text, list of exact phrases to mark — подстроки input_text)
EXAMPLES = [
    ("Раньше я сидел в фейсбуке каждый день.", ["фейсбуке"]),
    ("Скачай приложение с Facebook и Instagram для связи.", ["Facebook", "Instagram"]),
    ("Компания Meta владеет несколькими платформами.", ["Meta"]),
    ("Пиши мне в вотсап когда будешь свободен.", ["вотсап"]),
    ("Она ведет блог в инстаграме уже год.", ["инстаграме"]),
    ("Общение через WhatsApp запрещено правилами.", ["WhatsApp"]),
    ("У меня есть аккаунт в фейсбук с 2015 года.", ["фейсбук"]),
    ("Мы общались в инстаграм под псевдонимом.", ["инстаграм"]),
    ("Напиши в вотсапе завтра утром.", ["вотсапе"]),
    ("Мета платформа признана экстремистской в РФ.", ["Мета"]),
    ("Заходи на фейсбук и смотри новости там.", ["фейсбук"]),
    ("Дети сидят в инстаграме целый день.", ["инстаграме"]),
    ("Используют вотсап для связи с родными.", ["вотсап"]),
    ("Реклама в Facebook и Meta запрещена.", ["Facebook", "Meta"]),
    ("Зарегистрирован в инстаграм под ником.", ["инстаграм"]),
    ("Переписка в WhatsApp велась открыто.", ["WhatsApp"]),
    ("Бывший сотрудник Meta дал интервью.", ["Meta"]),
    ("Страница во фейсбуке набрала подписчиков.", ["фейсбуке"]),
    ("Подписчики в инстаграме оставили комментарии.", ["инстаграме"]),
    ("Группа в вотсапе создана для обсуждения.", ["вотсапе"]),
    ("Логотип Facebook на стене офиса.", ["Facebook"]),
    ("Приложение Instagram установлено на телефон.", ["Instagram"]),
    ("Сервис WhatsApp заблокирован провайдером.", ["WhatsApp"]),
    ("Холдинг Meta объявил о новых правилах.", ["Meta"]),
    ("Сидел в фейсбуке часами напролет.", ["фейсбуке"]),
    ("Фото в инстаграм загрузил вчера.", ["инстаграм"]),
    ("Созвон через вотсап состоялся.", ["вотсап"]),
    ("Реклама Facebook и Instagram запрещена законом.", ["Facebook", "Instagram"]),
    ("Политика Meta в отношении контента.", ["Meta"]),
    ("Пересылал файлы через WhatsApp.", ["WhatsApp"]),
]

NUM_TRAIN = 20
NUM_TEST = len(EXAMPLES) - NUM_TRAIN  # 11


def find_span(text: str, phrase: str):
    """Возвращает (start_char, end_char) для первого вхождения phrase в text."""
    pos = text.find(phrase)
    if pos == -1:
        return None, None
    return pos, pos + len(phrase)


def build_number_char_output(input_text: str, phrases: list) -> str:
    """Формат с start_char, end_char."""
    out_phrases = []
    for p in phrases:
        start, end = find_span(input_text, p)
        out_phrases.append({"text": p, "start_char": start, "end_char": end})
    return json.dumps({
        "found_extremism": True,
        "extremist_phrases": out_phrases,
        "categories": [CATEGORY],
    }, ensure_ascii=False)


def build_plain_output(phrases: list) -> str:
    """Формат без меток — только список строк."""
    return json.dumps({
        "found_extremism": True,
        "extremist_phrases": phrases,
        "categories": [CATEGORY],
    }, ensure_ascii=False)


def main():
    train_number_char = []
    test_number_char = []
    train_plain = []
    test_plain = []

    for i, (inp, phrases) in enumerate(EXAMPLES):
        row_instruction = INSTRUCTION
        obj_num = {
            "instruction": row_instruction,
            "input": inp,
            "output": build_number_char_output(inp, phrases),
        }
        obj_plain = {
            "instruction": row_instruction,
            "input": inp,
            "output": build_plain_output(phrases),
        }
        if i < NUM_TRAIN:
            train_number_char.append(obj_num)
            train_plain.append(obj_plain)
        else:
            test_number_char.append(obj_num)
            test_plain.append(obj_plain)

    # number_char
    path_train_nc = os.path.join(ROOT, "extremism_detection_dataset_number_char", "train_dataset.jsonl")
    path_test_nc = os.path.join(ROOT, "extremism_detection_dataset_number_char", "test_dataset.jsonl")
    for path, rows in [(path_train_nc, train_number_char), (path_test_nc, test_number_char)]:
        with open(path, "a", encoding="utf-8") as f:
            for obj in rows:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        print(path, "+", len(rows), "строк")

    # plain (без меток)
    path_train_plain = os.path.join(ROOT, "extremism_detection_dataset", "train_dataset.jsonl")
    path_test_plain = os.path.join(ROOT, "extremism_detection_dataset", "test_dataset.jsonl")
    for path, rows in [(path_train_plain, train_plain), (path_test_plain, test_plain)]:
        with open(path, "a", encoding="utf-8") as f:
            for obj in rows:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        print(path, "+", len(rows), "строк")

    print("Готово. Добавлено примеров с запрещёнными платформами: train", NUM_TRAIN, ", test", NUM_TEST)


if __name__ == "__main__":
    main()
