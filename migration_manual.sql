-- ============================================
-- РУЧНАЯ МИГРАЦИЯ БД
-- Дата: 2025-01-27
-- Описание: Добавление таблицы subjects и полей class_number, subject_id в templates
-- ============================================

-- ============================================
-- ДЛЯ POSTGRESQL
-- ============================================

-- 1. Создание таблицы subjects
CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    name_slug VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Создание индексов для subjects
CREATE INDEX IF NOT EXISTS ix_subjects_name_slug ON subjects(name_slug);
CREATE INDEX IF NOT EXISTS ix_subjects_is_active ON subjects(is_active);

-- 3. Добавление полей в таблицу templates
ALTER TABLE templates ADD COLUMN IF NOT EXISTS class_number INTEGER;
ALTER TABLE templates ADD COLUMN IF NOT EXISTS subject_id INTEGER;

-- 4. Создание индекса на subject_id
CREATE INDEX IF NOT EXISTS ix_templates_subject_id ON templates(subject_id);

-- 5. Удаление старого уникального индекса (если существует)
DROP INDEX IF EXISTS idx_username_topic_slug;

-- 6. Создание нового уникального индекса
-- ВАЖНО: Этот индекс требует, чтобы subject_id был NOT NULL
-- Если в таблице есть записи с NULL в subject_id, сначала обновите их
CREATE UNIQUE INDEX IF NOT EXISTS idx_username_subject_topic 
ON templates(created_by_username, subject_id, topic_slug);

-- ============================================
-- ДЛЯ SQLITE
-- ============================================

-- 1. Создание таблицы subjects
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL UNIQUE,
    name_slug VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Создание индексов для subjects
CREATE INDEX IF NOT EXISTS ix_subjects_name_slug ON subjects(name_slug);
CREATE INDEX IF NOT EXISTS ix_subjects_is_active ON subjects(is_active);

-- 3. Добавление полей в таблицу templates
-- SQLite не поддерживает IF NOT EXISTS для ALTER TABLE ADD COLUMN
-- Проверьте наличие колонок перед добавлением
-- Если колонки уже существуют, пропустите эти команды
ALTER TABLE templates ADD COLUMN class_number INTEGER;
ALTER TABLE templates ADD COLUMN subject_id INTEGER;

-- 4. Создание индекса на subject_id
CREATE INDEX IF NOT EXISTS ix_templates_subject_id ON templates(subject_id);

-- 5. Удаление старого уникального индекса (если существует)
DROP INDEX IF EXISTS idx_username_topic_slug;

-- 6. Создание нового уникального индекса
CREATE UNIQUE INDEX IF NOT EXISTS idx_username_subject_topic 
ON templates(created_by_username, subject_id, topic_slug);

-- ============================================
-- ПРОВЕРКА МИГРАЦИИ
-- ============================================

-- Проверьте структуру таблицы subjects
-- PostgreSQL: \d subjects
-- SQLite: .schema subjects

-- Проверьте структуру таблицы templates
-- PostgreSQL: \d templates
-- SQLite: .schema templates

-- Проверьте индексы
-- PostgreSQL: \di
-- SQLite: .indices templates

-- ============================================
-- ОТКАТ МИГРАЦИИ (если нужно)
-- ============================================

-- Для PostgreSQL и SQLite:
-- DROP INDEX IF EXISTS idx_username_subject_topic;
-- CREATE UNIQUE INDEX IF EXISTS idx_username_topic_slug ON templates(created_by_username, topic_slug);
-- ALTER TABLE templates DROP COLUMN IF EXISTS subject_id;
-- ALTER TABLE templates DROP COLUMN IF EXISTS class_number;
-- DROP TABLE IF EXISTS subjects;


