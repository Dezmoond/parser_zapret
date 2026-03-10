# Instruction-датасет для дообучения Llama на извлечение сущностей

## Назначение

Датасет для дообучения LLM на задачу: по чанку текста извлекать сущности и возвращать **только валидный JSON**. Классы (без other — избыточно для Llama):

- `persons` — ФИО (fio)
- `organizations` — названия организаций (organization)
- `titles` — названия книг/фильмов/песен (title)
- `urls` — интернет-ссылки (url)

## Файлы

| Файл | Описание |
|------|----------|
| `instruction_dataset_100k.jsonl` | 100 000 обучающих примеров |
| `instruction_dataset_test.jsonl` | 10 000 **тестовых** примеров (нет пересечения по `input` с 100k) |
| `instruction_dataset_10k.jsonl` | 10 000 примеров — срез из 100k для быстрой проверки |
| `build_instruction_dataset.py` | Скрипт генерации датасета |

## Формат одной строки (JSONL)

```json
{
  "instruction": "Извлеки сущности из текста и верни JSON с полями: persons, organizations, titles, urls. Только валидный JSON, без пояснений.",
  "input": "Текст из 4–5 предложений с упоминаниями ФИО, организаций, названий, ссылок.",
  "output": "{\"persons\": [\"...\"], \"organizations\": [\"...\"], \"titles\": [], \"urls\": []}"
}
```

## Как создан датасет

- **Классы:** fio, organization, title, url (other не используется).
- **Контекст (input):** чанки по 4–5 предложений из `курсовая.txt`.
- **Сущности:** из `drobimdataset/dataset_01_expanded_only_white.csv`.
- В `output` — JSON с полями persons, organizations, titles, urls.

## Пересборка датасета

```bash
cd E:\CURSOR\DIPLOM\dataset
python build_instruction_dataset.py
```

Нужны: `drobimdataset/dataset_01_expanded_only_white.csv`, `курсовая.txt` в той же папке `dataset`.

## Использование для дообучения Llama

1. Преобразовать JSONL в формат, ожидаемый вашим пайплайном (например, Alpaca/instruction format или собственный шаблон чата Llama).
2. Дообучить модель (full fine-tune или LoRA/QLoRA) на задачу: по `instruction` + `input` модель должна выдавать **только** строку из поля `output` (один JSON-объект).
3. В инференсе: подавать чанк текста как `input` с той же `instruction`, парсить ответ модели как JSON и извлекать списки сущностей.

Можно использовать frameworks: Hugging Face Transformers + PEFT (LoRA), Axolotl, LLaMA-Factory, unsloth и т.п., с указанием пути к `instruction_dataset_100k.jsonl` (или `10k`) как к обучающим данным.
