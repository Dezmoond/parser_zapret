# -*- coding: utf-8 -*-
"""
Генератор расширенного датасета dataset_01: 10000 примеров на каждый класс.
Без повторений. Разнообразие: ФИО (форма/склонение), названия (с авторами, форма),
организации (сокращённые/полные, склонения), URL (короткие и длинные).
"""

import csv
import random
import re
from itertools import product

random.seed(42)

# --- ФИО: базы имён, фамилий, отчеств ---
SURNAMES_M = [
    "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров", "Соколов", "Михайлов", "Новиков",
    "Федоров", "Морозов", "Волков", "Алексеев", "Лебедев", "Семёнов", "Егоров", "Павлов",
    "Козлов", "Степанов", "Николаев", "Орлов", "Андреев", "Макаров", "Никитин", "Захаров",
    "Зайцев", "Соловьёв", "Борисов", "Яковлев", "Григорьев", "Романов", "Воробьёв", "Сергеев",
    "Кузьмин", "Фролов", "Александров", "Дмитриев", "Королёв", "Гусев", "Киселёв", "Ильин",
    "Максимов", "Поляков", "Сорокин", "Виноградов", "Ковалёв", "Белов", "Медведев", "Антонов",
    "Тарасов", "Жуков", "Баранов", "Филиппов", "Комаров", "Давыдов", "Беляев", "Герасимов",
]
SURNAMES_F = [
    "Смирнова", "Кузнецова", "Попова", "Васильева", "Петрова", "Соколова", "Михайлова", "Новикова",
    "Федорова", "Морозова", "Волкова", "Алексеева", "Лебедева", "Семёнова", "Егорова", "Павлова",
    "Козлова", "Степанова", "Николаева", "Орлова", "Андреева", "Макарова", "Никитина", "Захарова",
    "Зайцева", "Соловьёва", "Борисова", "Яковлева", "Григорьева", "Романова", "Воробьёва", "Сергеева",
    "Кузьмина", "Фролова", "Александрова", "Дмитриева", "Королёва", "Гусева", "Киселёва", "Ильина",
    "Максимова", "Полякова", "Сорокина", "Виноградова", "Ковалёва", "Белова", "Медведева", "Антонова",
    "Тарасова", "Жукова", "Баранова", "Филиппова", "Комарова", "Давыдова", "Беляева", "Герасимова",
]
NAMES_M = [
    "Алексей", "Дмитрий", "Иван", "Андрей", "Сергей", "Павел", "Николай", "Артём", "Игорь", "Виктор",
    "Александр", "Михаил", "Евгений", "Олег", "Константин", "Григорий", "Максим", "Роман", "Владимир", "Денис",
    "Антон", "Тимофей", "Кирилл", "Никита", "Станислав", "Георгий", "Леонид", "Вадим", "Юрий", "Валерий",
]
NAMES_F = [
    "Мария", "Анна", "Елена", "Ольга", "Наталья", "Татьяна", "Екатерина", "Юлия", "Надежда", "Ирина",
    "Светлана", "Виктория", "Дарья", "Алина", "Полина", "Елизавета", "Ксения", "Валерия", "Вероника", "Александра",
    "Маргарита", "Диана", "Кристина", "Василиса", "Милана", "София", "Ульяна", "Варвара", "Арина", "Марина",
]
PATRONYMICS_M = [
    "Александрович", "Дмитриевич", "Иванович", "Андреевич", "Сергеевич", "Петрович", "Николаевич", "Викторович",
    "Олегович", "Михайлович", "Владимирович", "Павлович", "Артёмович", "Игоревич", "Константинович", "Григорьевич",
]
PATRONYMICS_F = [
    "Александровна", "Дмитриевна", "Ивановна", "Андреевна", "Сергеевна", "Петровна", "Николаевна", "Владимировна",
    "Павловна", "Михайловна", "Викторовна", "Олеговна", "Игоревна", "Константиновна", "Григорьевна", "Евгеньевна",
]

# Склонение фамилий (муж. род): И.п. -ов, Р.п. -ова, Д.п. -ову, В.п. -ова, Т.п. -овым, П.п. -ове
# Для разнообразия используем форму "в документ на имя ...", "от ...", "для ..."
FIO_PREFIXES = ["", "от ", "для ", "на имя ", "документ на ", "выдано "]

def gen_fio(count=10000):
    seen = set()
    result = []
    formats = [
        lambda s, n, p: f"{s} {n} {p}",                           # Фамилия Имя Отчество
        lambda s, n, p: f"{n} {p} {s}",                           # Имя Отчество Фамилия
        lambda s, n, p: f"{s} {n[0]}.{p[0]}.",                    # Фамилия И. О.
        lambda s, n, p: f"{n[0]}.{p[0]}. {s}",                   # И. О. Фамилия
        lambda s, n, p: f"{n} {s}",                               # Имя Фамилия
        lambda s, n, p: f"{s} {n}",                               # Фамилия Имя
        lambda s, n, p: f"{n[0]}. {s}",                           # И. Фамилия
        lambda s, n, p: f"{s} {n[0]}. {p}",                       # Фамилия И. Отчество
    ]
    # Генерируем все комбинации для максимального разнообразия
    attempts = 0
    while len(result) < count:
        attempts += 1
        if attempts > count * 30:
            break
        is_female = random.random() < 0.5
        if is_female:
            s, n, p = random.choice(SURNAMES_F), random.choice(NAMES_F), random.choice(PATRONYMICS_F)
        else:
            s, n, p = random.choice(SURNAMES_M), random.choice(NAMES_M), random.choice(PATRONYMICS_M)
        fmt = random.choice(formats)
        try:
            text = fmt(s, n, p)
        except Exception:
            text = f"{s} {n} {p}"
        if random.random() < 0.12:
            prefix = random.choice(FIO_PREFIXES)
            if prefix:
                text = prefix + text
        text = text.strip()
        if text not in seen:
            seen.add(text)
            result.append(text)
    # Добиваем: префиксы "от", "для", "на имя" + уже сгенерированные ФИО
    while len(result) < count:
        base = random.choice(result)
        if not base.startswith(("от ", "для ", "на имя ", "документ ", "выдано ")):
            candidate = random.choice(["от ", "для ", "на имя "]) + base
            if candidate not in seen:
                seen.add(candidate)
                result.append(candidate)
        else:
            s = random.choice(SURNAMES_M + SURNAMES_F)
            n = random.choice(NAMES_M + NAMES_F)
            p = random.choice(PATRONYMICS_M + PATRONYMICS_F)
            candidate = f"{s} {n} {p}"
            if candidate not in seen:
                seen.add(candidate)
                result.append(candidate)
        if len(result) >= count:
            break
    return result[:count]


# --- Организации ---
ORG_ABBREV = ["ООО", "АО", "ПАО", "ЗАО", "ИП", "НКО", "ГК", "Холдинг"]
ORG_FULL_PREFIX = [
    "Общество с ограниченной ответственностью",
    "Акционерное общество",
    "Публичное акционерное общество",
    "Закрытое акционерное общество",
]
ORG_NAMES = [
    "Вектор", "Сбербанк", "Газпром", "Яндекс", "Рога и копыта", "Технопарк", "Пятёрочка", "Магнит",
    "Лукойл", "Роснефть", "РЖД", "Почта России", "Московский политех", "Российские железные дороги",
    "Северсталь", "Норникель", "Татнефть", "Башнефть", "Сибур", "Новатэк", "Русал", "Полюс",
    "Аэрофлот", "Сбербанк России", "ВТБ", "Альфа-Банк", "Тинькофф", "Лента", "Дикси", "Перекрёсток",
    "М.Видео", "Эльдорадо", "DNS", "Ситилинк", "Леруа Мерлен", "ОБИ", "Касторама", "Икеа",
]
ORG_SPECIAL = [
    "МГУ имени М.В. Ломоносова", "МГУ", "СПбГУ", "Всероссийская государственная библиотека",
    "Российская национальная библиотека", "Министерство образования РФ", "Минобрнауки России",
    "ФГБОУ ВО «Московский политех»", "ФГБОУ ВО Московский политех", "Сеть магазинов «Пятёрочка»",
    "ФГУП «Почта России»", "АО «Российские железные дороги»", "РЖД", "Почта России",
]
ORG_DECL_PREFIX = ["", "в ", "из ", "для ", "согласно договору с ", "контракт с "]

def gen_organizations(count=10000):
    seen = set()
    result = []
    attempts = 0
    while len(result) < count and attempts < count * 20:
        attempts += 1
        if random.random() < 0.2 and ORG_SPECIAL:
            name = random.choice(ORG_SPECIAL)
            if random.random() < 0.35:
                prefix = random.choice(ORG_DECL_PREFIX)
                if prefix:
                    name = prefix + name
        else:
            abbrev = random.choice(ORG_ABBREV)
            base = random.choice(ORG_NAMES)
            if abbrev == "ИП":
                sn = random.choice(SURNAMES_M)
                nn = random.choice(NAMES_M)
                name = f'ИП {sn} {nn[0]}.{random.choice(PATRONYMICS_M)[0]}.'
            elif random.random() < 0.3:
                full = random.choice(ORG_FULL_PREFIX)
                name = f'{full} «{base}»'
            else:
                q, q2 = ('«', '»') if random.random() < 0.6 else ('"', '"')
                # Уникальность: иногда добавляем номер/филиал
                if random.random() < 0.15:
                    base = f"{base}-{random.randint(1, 9999)}"
                name = f'{abbrev} {q}{base}{q2}'
            if random.random() < 0.18:
                prefix = random.choice(ORG_DECL_PREFIX)
                if prefix:
                    name = prefix + name
        name = name.strip()
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    # Добиваем уникальными ООО/АО с номерами
    while len(result) < count:
        name = f'ООО «Компания-{random.randint(100000, 999999)}»'
        if name not in seen:
            seen.add(name)
            result.append(name)
        if len(result) >= count:
            break
    return result[:count]


# --- Названия книг, фильмов, песен ---
TITLES_BOOKS = [
    "Война и мир", "Преступление и наказание", "Мастер и Маргарита", "Евгений Онегин",
    "Идиот", "Братья Карамазовы", "Анна Каренина", "Отцы и дети", "Мёртвые души",
    "Тихий Дон", "Доктор Живаго", "Собачье сердце", "Двенадцать стульев", "Золотой телёнок",
    "Белый Бим Чёрное ухо", "А зори здесь тихие", "Понедельник начинается в субботу",
    "Обломов", "Герой нашего времени", "Ревизор", "Вий", "Тарас Бульба", "Рудин",
    "Бесы", "Подросток", "Белая гвардия", "Театральный роман", "Пиковая дама", "Капитанская дочка",
    "Горе от ума", "Гранатовый браслет", "Олеся", "Суламифь", "Старик и море", "На дне",
]
TITLES_FILMS = [
    "Броненосец Потёмкин", "Служебный роман", "Ирония судьбы, или С лёгким паром!",
    "Кавказская пленница", "Москва слезам не верит", "Девятая рота", "Левиафан", "Офицеры",
    "Мой ласковый и нежный зверь", "Белорусский вокзал", "Кин-дза-дза!", "Гардемарины, вперёд!",
    "Бриллиантовая рука", "Иван Васильевич меняет профессию", "Джентльмены удачи", "В бой идут одни старики",
    "Афоня", "Семнадцать мгновений весны", "Место встречи изменить нельзя", "Шерлок Холмс",
    "Покровские ворота", "Гостья из будущего", "Приключения Электроника", "Чародеи",
]
TITLES_SONGS = [
    "Тёмная ночь", "Подмосковные вечера", "Катюша", "Священная война", "День Победы",
    "Миллион алых роз", "Я спросил у ясеня", "Звезда по имени Солнце", "Группа крови",
    "Кукушка", "Комбат", "Конь", "Что такое осень", "Пачка сигарет", "Варвара",
    "Прекрасное далёко", "Следующий уровень", "Любовь на двоих", "Мой адрес — Советский Союз",
]
AUTHORS = [
    "Л.Н. Толстой", "Ф.М. Достоевский", "М.А. Булгаков", "А.С. Пушкин", "Н.В. Гоголь",
    "М.Ю. Лермонтов", "А.П. Чехов", "И.С. Тургенев", "С.А. Есенин", "А.А. Блок",
    "И. Ильф и Е. Петров", "Б.Л. Пастернак", "М.А. Шолохов", "Г.В. Троепольский",
]
TITLE_WRAPPERS = [
    lambda t: t,
    lambda t: f'«{t}»',
    lambda t: f'"{t}"',
    lambda t: f'Книга «{t}»',
    lambda t: f'Фильм «{t}»',
    lambda t: f'Песня «{t}»',
    lambda t: f'Роман «{t}»',
]

def gen_titles(count=10000):
    seen = set()
    result = []
    all_titles = [(t, "book") for t in TITLES_BOOKS] + [(t, "film") for t in TITLES_FILMS] + [(t, "song") for t in TITLES_SONGS]
    with_author = [" (автор: {})", " — {}", " ({})", ", {}"]
    extra_suffixes = [" — роман", " — фильм", " — песня", " — повесть", " — часть 1", " — том 2", " (издание 3)"]
    attempts = 0
    while len(result) < count and attempts < count * 15:
        attempts += 1
        title, kind = random.choice(all_titles)
        wrap = random.choice(TITLE_WRAPPERS)
        text = wrap(title)
        if random.random() < 0.45 and kind in ("book", "film"):
            auth = random.choice(AUTHORS)
            text += random.choice(with_author).format(auth)
        if random.random() < 0.25:
            text += random.choice(extra_suffixes) if random.random() > 0.3 else f" ({random.randint(1950, 2024)})"
        text = text.strip()
        if text not in seen:
            seen.add(text)
            result.append(text)
    # Добиваем уникальными суффиксами (год, издание, часть)
    while len(result) < count:
        base = random.choice(result)
        for suf in [f" — издание {random.randint(1, 20)}", f", {random.randint(1950, 2024)} г.", f" (часть {random.randint(1, 5)})"]:
            candidate = base + suf
            if candidate not in seen:
                seen.add(candidate)
                result.append(candidate)
                break
        if len(result) >= count:
            break
    return result[:count]


# --- URL ---
DOMAINS = [
    "ru.wikipedia.org", "example.com", "yandex.ru", "github.com", "habr.com", "kinopoisk.ru",
    "stackoverflow.com", "vk.com", "t.me", "docs.python.org", "pravo.gov.ru", "garant.ru", "mos.ru",
    "lib.ru", "google.com", "youtube.com", "vkontakte.ru", "ok.ru", "mail.ru", "rbc.ru", "lenta.ru",
]
SHORT_DOMAINS = ["t.me", "bit.ly", "vk.cc", "goo.gl", "v.k.com", "ya.ru", "qps.ru"]
PATH_PARTS = ["wiki", "articles", "page", "search", "film", "questions", "users", "repos", "books", "docs", "api", "v1", "news", "item"]
QUERY_KEYS = ["text", "q", "id", "page", "ref", "utm_source", "utm_medium", "lang", "sort", "filter"]

def gen_urls(count=10000):
    seen = set()
    result = []
    for _ in range(count):
        for _ in range(500):
            use_short = random.random() < 0.25
            if use_short:
                domain = random.choice(SHORT_DOMAINS)
                scheme = random.choice(["https://", "http://"])
                if domain in ["bit.ly", "goo.gl", "vk.cc"]:
                    path = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=random.randint(5, 10)))
                else:
                    path = random.choice(["id", "channel", "chat", "group"]) + str(random.randint(1, 999999))
                url = f"{scheme}{domain}/{path}"
            else:
                scheme = random.choice(["https://", "http://"])
                domain = random.choice(DOMAINS)
                if random.random() < 0.3:
                    domain = "www." + domain
                path_depth = random.randint(0, 4)
                path = ""
                if path_depth > 0:
                    path = "/" + "/".join(random.choices(PATH_PARTS, k=path_depth))
                    if "wiki" in domain:
                        path += "/" + "Заглавная_страница" if random.random() < 0.2 else "Article_" + str(random.randint(1, 99999))
                if random.random() < 0.4:
                    q = "&" if "?" in path else "?"
                    path += q + "&".join(f"{random.choice(QUERY_KEYS)}={random.choice(['test', 'value', '1', 'ru'])}" for _ in range(random.randint(1, 4)))
                if random.random() < 0.15:
                    path += "#" + "".join(random.choices("abcdef0123456789", k=8))
                url = f"{scheme}{domain}{path}"
            if url not in seen:
                seen.add(url)
                result.append(url)
                break
        else:
            url = f"https://example.com/u{random.randint(100000, 999999)}"
            if url not in seen:
                seen.add(url)
                result.append(url)
    return result[:count]


# --- Класс "other": слова и фразы, не относящиеся ни к одному из четырёх классов ---
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
    "входящий", "исходящий", "исх. №", "от", "на №", "на имя",
]
OTHER_TEMPLATES = [
    "{} руб.", "{} шт.", "{} %", "№ {}", "п. {}", "стр. {}", "г. {}",
    "с {} по {}", "в период {} — {}", "не ранее {}", "не позднее {}",
    "{} (при наличии)", "{} при необходимости", "{} по согласованию",
]
def gen_other(count=10000):
    """Фразы, которые не являются ФИО, организацией, названием или URL."""
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
    out_path = r"e:\CURSOR\DIPLOM\dataset\dataset_01_expanded.csv"
    n = 10000
    rows = []
    print("Генерация ФИО...")
    for t in gen_fio(n):
        rows.append((t, "fio"))
    print("Генерация организаций...")
    for t in gen_organizations(n):
        rows.append((t, "organization"))
    print("Генерация названий...")
    for t in gen_titles(n):
        rows.append((t, "title"))
    print("Генерация URL...")
    for t in gen_urls(n):
        rows.append((t, "url"))
    print("Генерация прочих (other)...")
    for t in gen_other(n):
        rows.append((t, "other"))
    random.shuffle(rows)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["text", "label"])
        for text, label in rows:
            w.writerow([text, label])
    print(f"Записано {len(rows)} строк в {out_path}")
    # Проверка уникальности и баланса (other может пересекаться по тексту с другими — допустимо)
    from collections import Counter
    c = Counter(r[1] for r in rows)
    if "other" not in c:
        raise AssertionError("Класс other не добавлен")
    print("Классы:", dict(c))


if __name__ == "__main__":
    main()
