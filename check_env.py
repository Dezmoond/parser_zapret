# -*- coding: utf-8 -*-
"""
Проверка окружения перед запуском chat_llama.py:
  - версия Python (рекомендуется 3.10 или 3.11);
  - наличие и версии torch, transformers, accelerate.
Запуск: python check_env.py
"""

import sys

MIN_PYTHON = (3, 8)
RECOMMENDED_PYTHON = (3, 10)  # 3.10 или 3.11 — оптимально для torch/transformers

def python_ok():
    v = sys.version_info
    current = (v.major, v.minor)
    ok = current >= MIN_PYTHON
    recommended = RECOMMENDED_PYTHON <= current <= (3, 12)
    return ok, recommended, f"{v.major}.{v.minor}.{v.micro}"

def main():
    print("Проверка окружения для llama_test\n" + "=" * 50)

    # Python
    ok, recommended, ver = python_ok()
    print(f"Python: {ver}")
    if not ok:
        print(f"  ОШИБКА: нужен Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} или новее.")
        sys.exit(1)
    if not recommended:
        print(f"  Рекомендуется Python 3.10 или 3.11 для стабильной работы torch/transformers.")
    else:
        print("  Версия подходит.")

    # Пакеты
    packages = [
        ("torch", "torch"),
        ("transformers", "transformers"),
        ("accelerate", "accelerate"),
    ]
    missing = []
    for name, module_name in packages:
        try:
            mod = __import__(module_name)
            ver = getattr(mod, "__version__", "?")
            print(f"{name}: {ver}")
        except ImportError:
            print(f"{name}: не установлен")
            missing.append(name)

    if missing:
        print("\nУстановите недостающие пакеты:")
        print("  pip install -r requirements.txt")
        print("Либо для CPU (без GPU):")
        print("  pip install torch --index-url https://download.pytorch.org/whl/cpu")
        print("  pip install -r requirements-cpu.txt")
        sys.exit(1)

    # Краткая проверка torch (без тяжёлой загрузки модели)
    try:
        import torch
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"\nУстройство torch: {dev}")
    except Exception as e:
        print(f"\nОшибка при импорте torch: {e}")
        sys.exit(1)

    print("\nОкружение в порядке. Можно запускать: python chat_llama.py")

if __name__ == "__main__":
    main()
