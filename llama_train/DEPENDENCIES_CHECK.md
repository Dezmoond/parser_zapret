# Проверка зависимостей перед сборкой образа Unsloth

**Перед изменением `requirements_unsloth_base.txt`, `constraints_unsloth.txt` или Dockerfile — выполнить проверку.**

## 1. Импорты в коде обучения

Проверить все импорты в `train_finetune_unsloth.py`:

| Импорт | Пакет | Примечание |
|--------|--------|------------|
| `os`, `json`, `pathlib` | stdlib | — |
| `datasets.Dataset` | datasets | в requirements_unsloth_base.txt |
| `unsloth.FastLanguageModel` | unsloth | ставится отдельно (unsloth[cu121-torch250]) |
| `trl.SFTTrainer` | trl | в requirements_unsloth_base.txt |
| `transformers.TrainingArguments` | transformers | в requirements_unsloth_base.txt |

## 2. Версии, несовместимые с unsloth

- **huggingface_hub**: начиная с 0.26 убран внутренний модуль `utils._token`; unsloth импортирует `from huggingface_hub.utils._token import get_token` → падает с `ModuleNotFoundError`. Решение: `huggingface_hub>=0.23.2,<0.26.0` (0.23.2 — минимум для transformers 4.45.2). См. [unsloth#1148](https://github.com/unslothai/unsloth/issues/1148).

### Проверенная совместимость (PyPI requires_dist)

| Пакет | Требует huggingface_hub | Наш диапазон 0.23.2–0.25.x |
|-------|-------------------------|-----------------------------|
| transformers 4.45.2 | >=0.23.2, <1.0 | ✓ |
| datasets 2.18.0 | >=0.19.4 | ✓ |
| accelerate 0.33.0 | >=0.21.0 | ✓ |
| peft 0.13.2 | >=0.17.0 | ✓ |

## 3. Проверенный рабочий стек (образ torch 2.5.1 + cu121)

| Компонент | Версия | Источник |
|-----------|--------|----------|
| Базовый образ | pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime | Docker |
| torch / torchaudio / torchvision | 2.5.1 | образ (не менять) |
| xformers | 0.0.29.post1 | PyTorch index cu121 (requirements_unsloth_heavy.txt) |
| bitsandbytes | 0.43.3 | requirements_unsloth_heavy.txt |
| unsloth | по extra cu121-torch250 | pip, constraints: torch==2.5.1, transformers==4.45.2 |
| transformers | 4.45.2 | requirements_unsloth_base.txt + constraints |
| huggingface_hub | >=0.23.2, <0.26.0 | requirements + constraints |

Порядок установки: (1) requirements_unsloth_base.txt, (2) xformers по URL + bitsandbytes с `-c constraints_torch.txt`, (3) unsloth[cu121-torch250] с constraints_unsloth.txt.

**Соответствие кода сборке:** `train_finetune_unsloth.py` проверен на совместимость с этим стеком:
- `FastLanguageModel.from_pretrained(model_name=..., max_seq_length=..., dtype=None, load_in_4bit=False, trust_remote_code=True)` — API unsloth 2024.x.
- `FastLanguageModel.for_training(model)` и `FastLanguageModel.get_peft_model(..., use_gradient_checkpointing="unsloth", random_state=42)` — поддерживаются.
- `SFTTrainer(..., dataset_text_field="text", ...)` — корректно для trl 0.8.6 (в trl 0.15+ этот аргумент менялся).
- `merge_and_unload()` и `save_pretrained` — стандартный PEFT/transformers API.

## 4. Транзитивные и runtime-зависимости

Не все зависимости указаны в `install_requires` пакетов; часть импортируется в коде:

- **trl 0.8.6**: в `trl/trainer/utils.py` импортируется `rich.console` → добавить **rich** в requirements_unsloth_base.txt.
- **unsloth**: тянет trl, peft, transformers, datasets, accelerate; версии ограничены constraints_unsloth.txt (transformers==4.45.2).

## 5. Чеклист перед сборкой

- [ ] Все импорты из `train_finetune_unsloth.py` покрыты пакетами (напрямую или через зависимости).
- [ ] Для каждого установленного пакета проверены его зависимости и опциональные зависимости, которые реально импортируются в коде (например, rich для trl).
- [ ] Версии в constraints_unsloth.txt совместимы с unsloth[cu121-torch250] и не конфликтуют с requirements_unsloth_base.txt.
- [ ] После изменения требований пересобрать образ и один раз запустить контейнер до конца (или хотя бы до успешного импорта всех модулей).

## 6. Быстрая проверка импортов в контейнере

После сборки образа можно проверить импорты без полного запуска обучения:

```bash
docker run --rm llama-train-unsloth python -c "
from datasets import Dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
print('All imports OK')
"
```

Если какой-то импорт падает — недостающий пакет добавить в requirements_unsloth_base.txt и пересобрать.
