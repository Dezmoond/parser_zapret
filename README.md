# Тестирование общения с Llama

Интерактивный чат с моделью **Llama-3.2-3B-Instruct** в терминале.

---

## Команды запуска

Из корня проекта (`llama_test`):

| Действие | Команда |
|----------|---------|
| **Запуск обучения** (дообучение Unsloth/LoRA) | `python llama_train/train_finetune_unsloth.py` |
| **Запуск чата** (интерактивный чат с моделью) | `python chat_llama.py` |
| **Запуск теста** (оценка на тестовом датасете) | `python llama_train/test_evaluate.py` |

Перед обучением: `pip install -r llama_train/requirements_unsloth.txt`. Перед чатом/тестом: `pip install -r requirements.txt`.

---

## Что нужно для запуска

### 1. Железо

| Требование | Описание |
|------------|----------|
| **GPU** | Желательно NVIDIA с 6+ ГБ VRAM (для 3B модели). Без GPU скрипт запустится на CPU, но ответы будут медленными. |
| **CUDA** | Если используете GPU: установите [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) и ставьте PyTorch с поддержкой CUDA (см. ниже). |
| **ОЗУ** | Рекомендуется 8+ ГБ. На CPU нужно больше. |
| **Место на диске** | Модель ~6 ГБ плюс зависимости. |

### 2. Python и пакеты

- **Python** 3.8–3.12. Рекомендуется **3.10 или 3.11** (меньше проблем с DLL и зависимостями на Windows).
- Проверить версию и пакеты:
  ```bash
  python check_env.py
  ```
- Установка зависимостей:

```bash
cd llama_test
pip install -r requirements.txt
```

Или вручную:

```bash
pip install torch transformers accelerate
```

Для **GPU**: установите PyTorch с CUDA (под свою версию CUDA):

```bash
# Пример для CUDA 11.8
pip install torch --index-url https://download.pytorch.org/whl/cu118
pip install transformers accelerate
```

Проверка GPU в Python:

```python
import torch
print(torch.cuda.is_available())  # True — GPU будет использоваться
```

### 3. Модель

- Папка с моделью должна быть по пути: `H:/anaconda/Lama5/Lama5/Llama-3.2-3B-Instruct`.
- В ней должны быть файлы в формате Hugging Face (например, `config.json`, `pytorch_model.bin` или `.safetensors`, токенизатор).

Если модель лежит в другом месте — задайте переменную окружения `MODEL_PATH` или измените значение по умолчанию в `chat_llama.py`.

---

## Запуск через Docker (GPU)

Контейнер с Python, PyTorch (CUDA 12.1) и всеми библиотеками. Модель считается на **GPU** внутри контейнера.

**Требования:**

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) для Windows (или Docker + nvidia-container-toolkit на Linux).
- **Видеокарта NVIDIA** и актуальный [драйвер](https://www.nvidia.com/Download/index.aspx).
- На Windows: в Docker Desktop включён **WSL 2** и в нём доступна GPU (обычно достаточно драйвера на хосте и обновления Docker Desktop).

**1. Сборка образа**

В папке `llama_test`:

```powershell
docker compose build
```

или:

```powershell
docker build -t llama-chat .
```

**2. Запуск чата**

Модель должна лежать на хосте (например, `H:\anaconda\Lama5\Lama5\Llama-3.2-3B-Instruct`). Контейнер подмонтирует эту папку в `/model` и использует GPU.

Через Docker Compose (при необходимости создайте `.env` с `MODEL_HOST_PATH=ваш/путь/к/модели`):

```powershell
docker compose run --rm llama-chat
```

Через `docker run` (флаг `--gpus all` обязателен для GPU):

```powershell
docker run -it --rm --gpus all -v "H:/anaconda/Lama5/Lama5/Llama-3.2-3B-Instruct:/model" llama-chat
```

После загрузки модели вводите сообщения в терминале. В начале должно вывестись `Устройство: cuda`. Выход: `/quit` или Ctrl+C.

**Переменные окружения**

| Переменная | Описание |
|------------|----------|
| `MODEL_PATH` | Путь к модели внутри контейнера (по умолчанию `/model`). На хосте папка монтируется через `-v`. |

---

## Запуск без Docker (локально)

```powershell
cd llama_test
python chat_llama.py
```

При старте выведется `Устройство: cuda` или `Устройство: cpu`. После загрузки вводите сообщения в терминале.

## Команды в чате

| Команда   | Действие           |
|----------|--------------------|
| `/clear` | Очистить историю   |
| `/quit` или `/exit` | Выход из чата |

## Зависимости (requirements.txt)

- `torch` — расчёты и работа с GPU/CPU
- `transformers` — загрузка модели и токенизатора
- `accelerate` — удобная загрузка больших моделей

---

## Ошибка TensorFlow (DLL) на Windows без GPU

Если при запуске появляется **ImportError** или **DLL load failed** при загрузке TensorFlow — для чата с Llama TensorFlow не нужен, его подтягивает новая версия `transformers`.

**Что уже сделано в скрипте:** в начале `chat_llama.py` выставлены `TRANSFORMERS_NO_TF=1` и подставлена заглушка для `tensorflow`, чтобы не загружать сломанные DLL.

**Если ошибка всё равно есть:**

1. **Удалить TensorFlow** (в окружении, где запускаете чат):
   ```bash
   pip uninstall tensorflow
   ```
   Затем снова запустить `python chat_llama.py`. Если появится «No module named 'tensorflow'», поставить более старую версию transformers:
   ```bash
   pip install "transformers>=4.36,<4.46"
   ```

2. **Отдельное окружение без TensorFlow** (рекомендуется):
   ```bash
   conda create -n llama_chat python=3.10 -y
   conda activate llama_chat
   pip install torch transformers accelerate
   cd E:\CURSOR\DIPLOM\llama_test
   python chat_llama.py
   ```
   В таком окружении TensorFlow не ставится — конфликта с DLL не будет.

---

## Ошибка PyTorch: c10.dll / WinError 1114 (нет GPU)

Если при запуске падает **OSError: WinError 1114** при загрузке `c10.dll` или других DLL из `torch` — обычно виновата сборка PyTorch под CUDA или отсутствие Visual C++ Redistributable.

**Что сделать по шагам:**

### 1. Установить Visual C++ Redistributable (если ещё не стоит)

Скачать и установить **Microsoft Visual C++ Redistributable (latest)**:
- https://aka.ms/vs/17/release/vc_redist.x64.exe (64-bit)

После установки перезапустить терминал и снова запустить скрипт.

### 2. Поставить PyTorch только под CPU (рекомендуется без GPU)

В том же окружении, где запускаете чат (например, `venv`):

```powershell
pip uninstall torch -y
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers accelerate
```

Затем снова:

```powershell
python chat_llama.py
```

CPU-версия PyTorch не тянет CUDA-библиотеки и реже даёт сбои DLL на Windows. Скрипт сам выберет `cpu` и будет работать (медленнее, чем на GPU).

### 3. Если ошибка осталась

- Зайти в `venv`, удалить папку `venv\Lib\site-packages\torch` и заново установить torch CPU (команды выше).
- Либо создать новое виртуальное окружение и поставить только CPU-пакеты:

```powershell
python -m venv venv_cpu
.\venv_cpu\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers accelerate
python chat_llama.py
```
