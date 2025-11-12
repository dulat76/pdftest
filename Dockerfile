FROM python:3.11-slim-bullseye

# 1. Установка системных зависимостей для PyMuPDF и Pillow
# build-essential: для компиляции C-расширений (fitz/PyMuPDF)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libfreetype6-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Установка рабочей директории
WORKDIR /app

# 3. Копирование файла зависимостей
COPY requirements.txt .

# 4. Установка ВСЕХ Python-зависимостей из файла
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копирование кода приложения
COPY . .

# 6. Команда запуска
CMD ["gunicorn", "-c", "gunicorn_conf.py", "app:app"]