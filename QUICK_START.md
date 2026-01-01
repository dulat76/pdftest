# Быстрый старт - Создание супер-пользователя

## Проблема: БД недоступна

Если удаленная PostgreSQL БД недоступна, используйте локальную SQLite БД для разработки.

## Решение 1: Использовать локальную SQLite БД

1. Создайте файл `.env` в корне проекта:
```env
DATABASE_URL=sqlite:///local_dev.db
DB_SCHEMA=public
```

2. Запустите скрипт создания супер-пользователя:
```bash
python setup_local_db.py
```

3. Запустите приложение:
```bash
python app.py
```

4. Войдите с:
   - Логин: `baseke`
   - Пароль: `changeme123`

## Решение 2: Настроить подключение к PostgreSQL

1. Убедитесь, что PostgreSQL сервер доступен на `185.22.64.9:5432`

2. Проверьте настройки в `.env`:
```env
DATABASE_URL=postgresql://flask_user:flask_password123@185.22.64.9:5432/flask_db
DB_SCHEMA=public
```

3. Примените миграции:
```bash
alembic upgrade head
```

4. Создайте супер-пользователя:
```bash
python init_superuser.py
```

## Проверка подключения к БД

Запустите:
```bash
python check_superuser.py
```

Этот скрипт проверит подключение и создаст/проверит супер-пользователя.




