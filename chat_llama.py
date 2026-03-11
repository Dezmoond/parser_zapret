# -*- coding: utf-8 -*-
"""
Интерактивное общение с Llama-3.2-3B-Instruct в терминале.
Модель: H:/anaconda/Lama5/Lama5/Llama-3.2-3B-Instruct
"""
# Отключаем TensorFlow — для Llama нужен только PyTorch (избегаем ошибки DLL на Windows)
import os
import sys
import warnings

os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["USE_TF"] = "0"
# Убрать предупреждение о logits в консоль (v4.46+)
warnings.filterwarnings("ignore", message=".*logits.*model output.*")

# Заглушка для tensorflow, если он сломан (DLL) — transformers иногда тянет его через image_transforms
class _TFDummy:
    pass
if "tensorflow" not in sys.modules:
    sys.modules["tensorflow"] = _TFDummy()
    sys.modules["tensorflow.python"] = _TFDummy()

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Устройство:", device)

# Путь к модели: из переменной окружения (Docker) или по умолчанию локальный
MODEL_PATH = os.environ.get("MODEL_PATH", "H:/anaconda/Lama5/Lama5/Llama-3.2-3B-Instruct")

# Показать, откуда грузим; проверить, что папка смонтирована (Docker)
print("Путь к модели:", MODEL_PATH)
if os.path.isdir(MODEL_PATH):
    files = os.listdir(MODEL_PATH)
    print("Файлов в папке модели:", len(files), "(загрузка с диска, не из интернета)")
else:
    print("ВНИМАНИЕ: папка модели не найдена, возможна загрузка из интернета!")

print("Загрузка токенизатора...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)

print("Загрузка модели (чтение чанков с диска)...")
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True).to(device)

# Исправление pad_token_id при необходимости
if isinstance(model.config.pad_token_id, list):
    model.config.pad_token_id = model.config.pad_token_id[0]
if model.config.pad_token_id is None:
    eos = model.config.eos_token_id
    model.config.pad_token_id = eos[0] if isinstance(eos, list) else eos

# Формат чата Llama 3.2 (система + диалог)
BOS = tokenizer.bos_token_id or tokenizer.convert_tokens_to_ids("<|begin_of_text|>")
EOS = tokenizer.eos_token_id

# Специальные токены для шаблона чата Llama 3.2
# Используем стандартный chat template, если есть
if hasattr(tokenizer, "chat_template") and tokenizer.chat_template:
    use_chat_template = True
else:
    use_chat_template = False

messages = []


def build_prompt(user_text: str) -> str:
    """Собирает промпт из истории и нового сообщения."""
    messages.append({"role": "user", "content": user_text})
    if use_chat_template:
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        # У части шаблонов (Llama 3.x) возвращается list of token ids, а не строка
        if isinstance(prompt, list):
            prompt = tokenizer.decode(prompt, skip_special_tokens=False)
    else:
        # Простой формат: [User] ... [Assistant]
        parts = []
        for m in messages:
            role = "User" if m["role"] == "user" else "Assistant"
            parts.append(f"{role}: {m['content']}")
        prompt = "\n".join(parts) + "\nAssistant:"
    return prompt


def generate_reply(user_text: str, max_new_tokens: int = 512) -> str:
    """Генерирует ответ модели. Извлекаем только новые токены — так ответ всегда корректен."""
    prompt = build_prompt(user_text)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    input_length = inputs["input_ids"].shape[1]

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            top_p=0.9,
            temperature=0.7,
            top_k=50,
            pad_token_id=model.config.pad_token_id,
            eos_token_id=EOS,
        )

    # Декодируем только сгенерированную часть (без промпта)
    new_token_ids = output[0][input_length:]
    reply = tokenizer.decode(new_token_ids, skip_special_tokens=True).strip()
    # Убрать возможные артефакты шаблона в начале (например <|eot_id|> или повтор "Assistant:")
    for prefix in ("Assistant:", "assistant", "<|end_of_text|>"):
        if reply.lower().startswith(prefix.lower()):
            reply = reply[len(prefix):].strip()
    if reply.startswith(":"):
        reply = reply[1:].strip()
    messages.append({"role": "assistant", "content": reply})
    return reply


def main():
    print("\n" + "=" * 50)
    print("Чат с Llama-3.2-3B-Instruct")
    print("Команды: /clear — очистить историю, /quit или /exit — выход")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("/quit", "/exit", "выход"):
            print("До свидания.")
            break
        if user_input.lower() == "/clear":
            messages.clear()
            print("[История очищена]\n")
            continue

        print("Модель: ", end="", flush=True)
        reply = generate_reply(user_input)
        print(reply)
        print()


if __name__ == "__main__":
    main()
