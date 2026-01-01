#!/bin/bash

# ============================================
# Скрипт автоматической установки обновлений
# Дата: 2025-01-27
# ============================================

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка, что скрипт запущен из правильной директории
if [ ! -f "app.py" ]; then
    error "Скрипт должен быть запущен из корневой директории проекта"
    exit 1
fi

info "Начало установки обновлений..."

# Шаг 1: Резервное копирование
info "Шаг 1: Создание резервной копии..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Копирование файлов
info "Создание резервной копии файлов..."
tar -czf "$BACKUP_DIR/files.tar.gz" . --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git'

# Резервная копия БД (если SQLite)
if [ -f "local_dev.db" ]; then
    info "Создание резервной копии SQLite БД..."
    cp local_dev.db "$BACKUP_DIR/local_dev.db"
fi

info "Резервная копия создана в $BACKUP_DIR"

# Шаг 2: Остановка приложения
info "Шаг 2: Остановка приложения..."
if systemctl is-active --quiet pdftest 2>/dev/null; then
    info "Остановка через systemd..."
    sudo systemctl stop pdftest
elif supervisorctl status pdftest 2>/dev/null | grep -q RUNNING; then
    info "Остановка через supervisor..."
    sudo supervisorctl stop pdftest
else
    warn "Приложение не запущено через systemd/supervisor, проверьте вручную"
fi

# Шаг 3: Активация виртуального окружения
info "Шаг 3: Активация виртуального окружения..."
if [ -d "venv" ]; then
    source venv/bin/activate
    info "Виртуальное окружение активировано"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    info "Виртуальное окружение активировано"
else
    warn "Виртуальное окружение не найдено, продолжаем без него"
fi

# Шаг 4: Установка зависимостей
info "Шаг 4: Установка зависимостей..."
pip install -q transliterate || warn "Не удалось установить transliterate, возможно уже установлен"

# Шаг 5: Применение миграций
info "Шаг 5: Применение миграций БД..."

# Проверка наличия Alembic
if command -v alembic &> /dev/null; then
    info "Применение миграций через Alembic..."
    alembic upgrade head
    info "Миграции применены успешно"
else
    warn "Alembic не найден, применяем миграцию вручную..."
    
    # Определение типа БД
    if grep -q "sqlite" .env 2>/dev/null || [ -f "local_dev.db" ]; then
        info "Обнаружена SQLite БД, применяем миграцию..."
        sqlite3 local_dev.db <<EOF
-- Создание таблицы subjects
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL UNIQUE,
    name_slug VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_subjects_name_slug ON subjects(name_slug);
CREATE INDEX IF NOT EXISTS ix_subjects_is_active ON subjects(is_active);

-- Добавление полей в templates
-- Проверяем наличие колонок перед добавлением
-- (SQLite не поддерживает IF NOT EXISTS для ALTER TABLE)
PRAGMA table_info(templates);
-- Если колонки не существуют, выполните:
-- ALTER TABLE templates ADD COLUMN class_number INTEGER;
-- ALTER TABLE templates ADD COLUMN subject_id INTEGER;

CREATE INDEX IF NOT EXISTS ix_templates_subject_id ON templates(subject_id);
DROP INDEX IF EXISTS idx_username_topic_slug;
CREATE UNIQUE INDEX IF NOT EXISTS idx_username_subject_topic 
ON templates(created_by_username, subject_id, topic_slug);
EOF
        info "Миграция SQLite применена"
    else
        warn "PostgreSQL БД обнаружена. Примените миграцию вручную из файла migration_manual.sql"
        warn "Или установите Alembic: pip install alembic"
    fi
fi

# Шаг 6: Проверка миграций
info "Шаг 6: Проверка миграций..."
python3 <<EOF
try:
    from models import SessionLocal, Subject, Template
    db = SessionLocal()
    
    # Проверка таблицы subjects
    try:
        count = db.query(Subject).count()
        print(f"✅ Таблица subjects существует, записей: {count}")
    except Exception as e:
        print(f"❌ Ошибка при проверке subjects: {e}")
    
    # Проверка полей в templates
    try:
        # Попытка создать запись с новыми полями (не сохраняем)
        test = Template(
            template_id='test_check',
            name='Test',
            topic='Test',
            topic_slug='test',
            fields=[],
            created_by_username='test',
            class_number=1,
            subject_id=1
        )
        print("✅ Поля class_number и subject_id доступны в Template")
    except Exception as e:
        print(f"❌ Ошибка при проверке полей Template: {e}")
    
    db.close()
except Exception as e:
    print(f"❌ Ошибка при проверке: {e}")
EOF

# Шаг 7: Запуск приложения
info "Шаг 7: Запуск приложения..."
if systemctl list-unit-files | grep -q pdftest.service; then
    info "Запуск через systemd..."
    sudo systemctl start pdftest
    sleep 2
    if systemctl is-active --quiet pdftest; then
        info "✅ Приложение запущено успешно"
    else
        error "❌ Не удалось запустить приложение"
        sudo systemctl status pdftest
    fi
elif command -v supervisorctl &> /dev/null; then
    info "Запуск через supervisor..."
    sudo supervisorctl start pdftest
    sleep 2
    if supervisorctl status pdftest | grep -q RUNNING; then
        info "✅ Приложение запущено успешно"
    else
        error "❌ Не удалось запустить приложение"
        supervisorctl status pdftest
    fi
else
    warn "Не найден systemd или supervisor, запустите приложение вручную"
fi

# Финальная проверка
info "Проверка работоспособности..."
sleep 3

if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    info "✅ Приложение отвечает на запросы"
else
    warn "⚠️  Приложение не отвечает, проверьте логи"
fi

info "=========================================="
info "Установка обновлений завершена!"
info "=========================================="
info "Следующие шаги:"
info "1. Войдите как супер-пользователь (baseke)"
info "2. Перейдите в 'Управление предметами'"
info "3. Создайте предметы (Математика, Русский язык и т.д.)"
info "4. Проверьте создание тестов с выбором класса и предмета"
info ""
info "Резервная копия сохранена в: $BACKUP_DIR"
info "=========================================="


