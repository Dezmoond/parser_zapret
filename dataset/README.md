# Датасет для классификации типов текстовых сущностей

**Классы:**
- `fio` — ФИО (физическое лицо)
- `organization` — Название организации
- `title` — Название песни / книги / фильма
- `url` — Интернет-ссылка

**Файлы датасета (10 форматов):**
| Файл | Формат | Описание |
|------|--------|----------|
| dataset_01.csv | CSV | text, label |
| dataset_02.json | JSON | Массив объектов { "text", "label" } |
| dataset_03.jsonl | JSON Lines | Один JSON-объект на строку |
| dataset_04.txt | Текст | Строки: LABEL \t текст |
| dataset_05.tsv | TSV | id, text, label |
| dataset_06.xml | XML | Корневой элемент с записями record |
| dataset_07.csv | CSV | id, text, label, source |
| dataset_08.md | Markdown | Таблица с примерами |
| dataset_09.yaml | YAML | Список записей |
| dataset_10.txt | Текст | Строки: текст \| label |

Использование: обучение и оценка моделей (RuBERT и др.) для выявления типа сущности в тексте.

Папка dataset/ — сборка и препроцессинг датасетов
Файл	Назначение
dataset/generate_dataset_01_expanded.py	Генерация расширенного датасета dataset_01 (по ~10000 примеров на класс, ФИО, организации, URL и т.п.)
dataset/build_instruction_dataset.py	Сборка инструкционного датасета (формат для обучения по инструкциям)
dataset/build_addition_from_sources.py	Добавление примеров в датасет из внешних источников
dataset/build_other_from_kursovaya.py	Формирование класса «other» из данных курсовой
dataset/build_blacklist_dataset.py (в dataset/blacklist/)	Сборка датасета из blacklist
dataset/add_other_class.py	Добавление класса «other» в датасет
dataset/shuffle_dataset.py	Перемешивание датасета
dataset/dedup_output_in_jsonl.py	Дедупликация выходных записей в JSONL
dataset/strip_output_prefixes.py	Удаление префиксов в выходных полях
dataset/drobimdataset/strip_prefixes_from_csv.py	Удаление префиксов в CSV (drobimdataset)
Папка extremism_detection_dataset/ — препроцессинг датасета экстремизма
Файл	Назначение
extremism_detection_dataset/normalize_specials.py	Нормализация спецсимволов
extremism_detection_dataset/simplify_instruction.py	Упрощение текста инструкции
extremism_detection_dataset/remove_quote_highlights.py	Удаление подсветки кавычек
extremism_detection_dataset/clean_quotes_in_phrases.py	Очистка кавычек в фразах
Папка extremism_detection_dataset_number_char/ — препроцессинг датасета (number_char)
Файл	Назначение
extremism_detection_dataset_number_char/normalize_specials.py	Нормализация спецсимволов
extremism_detection_dataset_number_char/simplify_instruction.py	Упрощение инструкции
extremism_detection_dataset_number_char/simplify_output.py	Упрощение выходного формата
extremism_detection_dataset_number_char/remove_quote_highlights.py	Удаление подсветки кавычек
extremism_detection_dataset_number_char/restore_phrase_spans.py	Восстановление спанов фраз
extremism_detection_dataset_number_char/set_lgbt_category.py	Установка категории ЛГБТ
extremism_detection_dataset_number_char/add_forbidden_platforms_examples.py	Добавление примеров запрещённых платформ

Корень проекта
Файл	Назначение
convert_to_dangerous_format.py	Конвертация датасетов в формат «опасные высказывания» (found_dangerous, dangerous_phrases, без categories)

