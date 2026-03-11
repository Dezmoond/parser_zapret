# Дообучение и тестирование Llama 3.2 на датасете экстремизма

## Структура

- **train_finetune.py** — дообучение модели на `extremism_detection_dataset_number_char/train_dataset.jsonl`.
- **train_finetune_unsloth.py** — то же задание через Unsloth (LoRA): быстрее и меньше VRAM; в конце LoRA объединяется с базой — одна готовая модель.
- **test_evaluate.py** — оценка модели на тестовом датасете: сравнение с эталоном, метрики (accuracy, precision, recall, F1), запись в лог. По умолчанию берёт модель из **output_unsloth** (объединённая после Unsloth).
- **chat_unsloth.py** — интерактивный чат для ручной проверки: вводите только текст для анализа, инструкция подставляется автоматически; модель — из **output_unsloth** (или `MODEL_PATH`).
- **Dockerfile.train** — образ для обычного дообучения (GPU).
- **Dockerfile.train.unsloth** — образ для обучения с Unsloth; в нём же можно запускать чат и тест на датасете (переопределением команды).

---

## 1. Обучение

### 1.1 Обычное дообучение (локально)

```bash
pip install -r llama_test/llama_train/requirements_train.txt
# Опционально: pip install flash-attn --no-build-isolation
# Переменные (по желанию): MODEL_PATH, TRAIN_DATASET, OUTPUT_DIR
python llama_test/llama_train/train_finetune.py
```

### 1.2 Обычное дообучение в Docker (GPU)

Нужны **NVIDIA Container Toolkit** и запуск с `--gpus all`. Из корня проекта (DIPLOM):

```bash
docker build -f llama_test/llama_train/Dockerfile.train -t llama-train .
```

**PowerShell (пример путей):**
```powershell
docker run --gpus all -v "H:/anaconda/Lama5/Lama5/Llama-3.2-3B-Instruct:/model" -v "E:/CURSOR/DIPLOM:/workspace" -v "E:/CURSOR/DIPLOM/llama_test/llama_train/output:/output" -e MODEL_PATH=/model -e TRAIN_DATASET=/workspace/extremism_detection_dataset_number_char/train_dataset.jsonl -e OUTPUT_DIR=/output llama-train
```

Модель сохраняется в `llama_test/llama_train/output`.

### 1.3 Дообучение с Unsloth (LoRA)

В конце обучения LoRA объединяется с базой и сохраняется **полная модель** (config.json + веса) в `output_unsloth` (не затирает `output`).

**Сборка образа:**
```bash
docker build -f llama_test/llama_train/Dockerfile.train.unsloth -t llama-train-unsloth .
```

**Запуск (PowerShell):**
```powershell
docker run --gpus all -v "H:/anaconda/Lama5/Lama5/Llama-3.2-3B-Instruct:/model" -v "E:/CURSOR/DIPLOM:/workspace" -v "E:/CURSOR/DIPLOM/llama_test/llama_train/output_unsloth:/output_unsloth" -e MODEL_PATH=/model -e TRAIN_DATASET=/workspace/extremism_detection_dataset_number_char/train_dataset.jsonl -e OUTPUT_DIR=/output_unsloth llama-train-unsloth
```

**Локально без Docker:**
```bash
pip install -r llama_test/llama_train/requirements_unsloth.txt
python llama_test/llama_train/train_finetune_unsloth.py
```

---

## 2. Чат (ручное тестирование)

Интерактивный режим: вы вводите только текст для анализа; инструкция из датасета подставляется автоматически. Используется объединённая модель после Unsloth (или путь из `MODEL_PATH`).

- Если в каталоге модели есть **config.json** — загружается одна объединённая модель.
- Если в каталоге только **адаптер** (adapter_config.json, adapter_model.safetensors, без config.json) — укажите **BASE_MODEL_PATH** (путь к базовой Llama); чат загрузит базу и адаптер, объединит их в памяти.

**Локально:**
```bash
# Модель по умолчанию: llama_test/llama_train/output_unsloth
python llama_test/llama_train/chat_unsloth.py
```

С указанием модели (PowerShell):
```powershell
$env:MODEL_PATH="E:\CURSOR\DIPLOM\llama_test\llama_train\output_unsloth"
python llama_test/llama_train/chat_unsloth.py
```

**В Docker (тот же образ llama-train-unsloth):**

Если в `output_unsloth` уже лежит полная объединённая модель (после переобучения с исправленным скриптом):
```powershell
docker run -it --gpus all -v "E:/CURSOR/DIPLOM/llama_test/llama_train/output_unsloth:/output_unsloth" -e MODEL_PATH=/output_unsloth llama-train-unsloth python chat_unsloth.py
```

Если в `output_unsloth` только адаптер (нет config.json), смонтируйте базу и задайте BASE_MODEL_PATH:
```powershell
docker run -it --gpus all -v "H:/anaconda/Lama5/Lama5/Llama-3.2-3B-Instruct:/model" -v "E:/CURSOR/DIPLOM/llama_test/llama_train/output_unsloth:/output_unsloth" -e MODEL_PATH=/output_unsloth -e BASE_MODEL_PATH=/model llama-train-unsloth python chat_unsloth.py
```

---

## 3. Тестирование на датасете

Скрипт **test_evaluate.py** прогоняет модель по `test_dataset.jsonl`, сравнивает ответы с эталоном по полю `found_extremism`, пишет метрики и матрицу путаницы в терминал и в лог.

- **Модель по умолчанию:** `llama_test/llama_train/output_unsloth` (объединённая модель после Unsloth).
- Чтобы тестировать модель обычного обучения (`output`), задайте `MODEL_PATH` на каталог `output`.

**Локально:**
```bash
pip install -r llama_test/llama_train/requirements_test.txt
python llama_test/llama_train/test_evaluate.py
```

**С указанием путей (PowerShell):**
```powershell
# Модель Unsloth (по умолчанию)
$env:MODEL_PATH="E:\CURSOR\DIPLOM\llama_test\llama_train\output_unsloth"
$env:TEST_DATASET="E:\CURSOR\DIPLOM\extremism_detection_dataset_number_char\test_dataset.jsonl"
$env:EVAL_LOG="E:\CURSOR\DIPLOM\llama_test\llama_train\evaluation.log"
python llama_test/llama_train/test_evaluate.py
```

Для модели из обычного обучения:
```powershell
$env:MODEL_PATH="E:\CURSOR\DIPLOM\llama_test\llama_train\output"
python llama_test/llama_train/test_evaluate.py
```

**В Docker (образ llama-train-unsloth):**

Смонтируйте каталог с моделью и датасет. Пример (PowerShell):

```powershell
docker run --gpus all -v "E:/CURSOR/DIPLOM/llama_test/llama_train/output_unsloth:/output_unsloth" -v "E:/CURSOR/DIPLOM/extremism_detection_dataset_number_char:/data" -e MODEL_PATH=/output_unsloth -e TEST_DATASET=/data/test_dataset.jsonl llama-train-unsloth python test_evaluate.py
```

Лог при этом пишется внутрь контейнера; чтобы сохранить на хост, добавьте монтирование и `EVAL_LOG`, например:

```powershell
docker run --gpus all -v "E:/CURSOR/DIPLOM/llama_test/llama_train/output_unsloth:/output_unsloth" -v "E:/CURSOR/DIPLOM/extremism_detection_dataset_number_char:/data" -v "E:/CURSOR/DIPLOM/llama_test/llama_train:/app_log" -e MODEL_PATH=/output_unsloth -e TEST_DATASET=/data/test_dataset.jsonl -e EVAL_LOG=/app_log/evaluation.log llama-train-unsloth python test_evaluate.py
```

В лог и в терминал выводятся: по каждому примеру — ввод, эталон, ответ модели, совпадение по `found_extremism`; в конце — Accuracy, Precision, Recall, F1, classification report и матрица путаницы.


ТЕСТ
docker run --rm --gpus all ^
  -v E:\CURSOR\DIPLOM\llama_test\output_unsloth:/model ^
  -v E:\CURSOR\DIPLOM\extremism_detection_dataset_number_char\test_dataset.jsonl:/data/test_dataset.jsonl ^
  -v E:\CURSOR\DIPLOM\llama_test\logs:/logs ^
  -e MODEL_PATH=/model ^
  -e TEST_DATASET=/data/test_dataset.jsonl ^
  -e EVAL_LOG=/logs/evaluation.log ^
  -e MAX_TEST_SAMPLES=0 ^
  llama-train-unsloth ^
  python /workspace/llama_test/llama_train/test_evaluate.py