# Чат с Llama-3.2-3B-Instruct в контейнере (GPU / NVIDIA CUDA)
# Требуется: Docker с поддержкой NVIDIA (nvidia-container-toolkit).
# Сборка: docker build -t llama-chat .
# Запуск: docker compose run --rm llama-chat  (или docker run с --gpus all)

# Базовый образ PyTorch с CUDA 12.1
FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# В базовом образе уже есть torch с CUDA — ставим только transformers и accelerate
COPY requirements-cpu.txt ./
RUN pip install --no-cache-dir -r requirements-cpu.txt

COPY chat_llama.py ./

ENV MODEL_PATH=/model

CMD ["python", "chat_llama.py"]
