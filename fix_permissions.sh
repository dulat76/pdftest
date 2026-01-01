#!/bin/bash
# Скрипт для исправления прав доступа к директориям Flask приложения

echo "Исправление прав доступа для Flask приложения..."

# Путь к директории приложения
APP_DIR="/home/ubuntu/predmet_kz/flask_app"

# Директории, которым нужны права на запись
DIRS=(
    "templates_json"
    "uploads"
    "logs"
)

# Изменить владельца всех директорий на ubuntu
echo "Изменение владельца директорий на ubuntu..."
sudo chown -R ubuntu:ubuntu "$APP_DIR"

# Установить права доступа для директорий
echo "Установка прав доступа..."
for dir in "${DIRS[@]}"; do
    DIR_PATH="$APP_DIR/$dir"
    if [ -d "$DIR_PATH" ]; then
        echo "  Установка прав для $dir..."
        sudo chmod -R 755 "$DIR_PATH"
    else
        echo "  Создание директории $dir..."
        sudo mkdir -p "$DIR_PATH"
        sudo chown ubuntu:ubuntu "$DIR_PATH"
        sudo chmod 755 "$DIR_PATH"
    fi
done

# Установить права на файлы в директориях
echo "Установка прав на файлы..."
for dir in "${DIRS[@]}"; do
    DIR_PATH="$APP_DIR/$dir"
    if [ -d "$DIR_PATH" ]; then
        sudo find "$DIR_PATH" -type f -exec chmod 644 {} \;
        sudo find "$DIR_PATH" -type d -exec chmod 755 {} \;
    fi
done

echo "Проверка прав доступа:"
ls -la "$APP_DIR" | grep -E "templates_json|uploads|logs"

echo ""
echo "Готово! Теперь перезапустите Flask приложение:"
echo "  sudo systemctl restart flask_app"

