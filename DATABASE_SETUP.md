# 🚀 Настройка подключения к удаленной БД

## Шаг 1: Создайте файл `.env`

Скопируйте `.env.example` в `.env`:

```bash
copy .env.example .env
```

## Шаг 2: Обновите `.env` следующими данными:

```env
# Gemini AI Configuration
GOOGLE_API_KEY=your_google_api_key_here

# Flask Configuration
SECRET_KEY=your_secret_key_here
DEBUG=True

# Application Settings
PDF_DPI=200
SESSION_TIMEOUT_HOURS=2

# AI Settings
AI_CHECKING_ENABLED=True
SIMILARITY_THRESHOLD=0.8
CACHE_AI_RESPONSES=True
LOG_AI_REQUESTS=True

# ============================================
# Remote PostgreSQL Database Configuration
# ============================================
DB_HOST=185.22.64.9
DB_PORT=5432
DB_NAME=flask_db
DB_USER=flask_user
DB_PASSWORD=flask_password123
DB_SCHEMA=public

# Full connection string
DATABASE_URL=postgresql://flask_user:flask_password123@185.22.64.9:5432/flask_db
```

## Шаг 3: Протестируйте подключение

```bash
python setup_remote_db.py
```

Этот скрипт:
- ✅ Проверит подключение к серверу 185.22.64.9
- ✅ Создаст схему `pdftest_schema` (если нужна изоляция)
- ✅ Проверит права доступа
- ✅ Покажет версию PostgreSQL

## Шаг 4: Примените миграции

После успешного подключения:

```bash
# Создать миграцию
alembic revision --autogenerate -m "add multi-school models"

# Применить миграцию
alembic upgrade head
```

---

## 💡 Изменение учетных данных БД

**Да, вы можете изменить данные в любое время!**

### Вариант 1: Изменить пароль существующего пользователя

```sql
ALTER USER flask_user WITH PASSWORD 'новый_пароль';
```

### Вариант 2: Создать нового пользователя

```sql
-- Создать нового пользователя
CREATE USER pdftest_user WITH PASSWORD 'secure_password_here';

-- Дать права на базу данных
GRANT ALL PRIVILEGES ON DATABASE flask_db TO pdftest_user;

-- Дать права на все таблицы
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO pdftest_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO pdftest_user;
```

### Вариант 3: Создать отдельную БД для pdftest

```sql
-- Создать новую БД
CREATE DATABASE pdftest_db OWNER flask_user;

-- Или с новым пользователем
CREATE USER pdftest_user WITH PASSWORD 'secure_password';
CREATE DATABASE pdftest_db OWNER pdftest_user;
```

**Рекомендация**: Я предлагаю использовать существующую `flask_db` для начала, а потом при необходимости можно создать отдельную БД.

---

## 🔒 Безопасность

> [!WARNING]
> Файл `.env` содержит пароли и **НЕ должен** коммититься в Git!
> Он уже добавлен в `.gitignore`

### Генерация безопасного SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Скопируйте результат в `.env` как `SECRET_KEY`

---

## 🧪 Проверка подключения

После создания `.env` файла, запустите:

```bash
python setup_remote_db.py
```

Вы должны увидеть:
```
✅ Подключение успешно!
📊 PostgreSQL версия: ...
✅ Схема pdftest_schema создана
```

---

## ❓ Возможные проблемы

### Проблема: Connection refused

**Решение**: Проверьте firewall на сервере:
```bash
# На сервере
sudo ufw allow 5432/tcp
```

### Проблема: Authentication failed

**Решение**: Проверьте `pg_hba.conf` на сервере:
```
# Добавить строку для удаленного доступа
host    flask_db    flask_user    0.0.0.0/0    md5
```

Затем перезапустить PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### Проблема: Timeout

**Решение**: Проверьте `postgresql.conf`:
```
listen_addresses = '*'
```

---

## 📝 Следующие шаги

После успешного подключения:

1. ✅ Создать модели для мультишкольной системы
2. ✅ Создать миграции Alembic
3. ✅ Применить миграции на удаленной БД
4. ✅ Начать разработку API

**Готовы продолжить?** 🚀
