# Инструкция по проверке логов при редактировании учителя

## 1. Проверка логов systemd (Flask приложение)

```bash
# Просмотр последних логов Flask приложения
sudo journalctl -u flask_app -n 100 --no-pager

# Просмотр логов в реальном времени
sudo journalctl -u flask_app -f

# Просмотр логов за последний час
sudo journalctl -u flask_app --since "1 hour ago" --no-pager

# Поиск ошибок в логах
sudo journalctl -u flask_app --no-pager | grep -i "error\|exception\|traceback\|UPDATE_TEACHER"
```

## 2. Проверка логов Gunicorn (если используется)

```bash
# Если логи Gunicorn пишутся в файл
tail -f /home/ubuntu/predmet_kz/flask_app/logs/gunicorn.log

# Или в systemd
sudo journalctl -u flask_app -n 200 --no-pager | grep -i "gunicorn"
```

## 3. Проверка логов через Python

```bash
# Запуск Python с подключением к БД для проверки
cd /home/ubuntu/predmet_kz/flask_app
source venv/bin/activate
python3 -c "
from models import SessionLocal, User
db = SessionLocal()
teacher = db.query(User).filter(User.role == 'teacher').first()
if teacher:
    print(f'Учитель найден: ID={teacher.id}, username={teacher.username}')
    print(f'Данные: first_name={teacher.first_name}, last_name={teacher.last_name}, email={teacher.email}')
else:
    print('Учителя не найдены')
db.close()
"
```

## 4. Проверка логов Nginx (если есть проблемы с проксированием)

```bash
# Логи доступа
sudo tail -f /var/log/nginx/access.log

# Логи ошибок
sudo tail -f /var/log/nginx/error.log
```

## 5. Тестирование API напрямую

```bash
# Получение токена (если нужна аутентификация)
# Затем тестирование PUT запроса
curl -X PUT http://localhost:5000/api/admin/teachers/1 \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{
    "first_name": "Тест",
    "last_name": "Тестов",
    "email": "test@test.com",
    "username": "test.test",
    "city": "Астана",
    "city_code": "ast",
    "school": "Школа 1",
    "school_code": "sch1"
  }'
```

## 6. Проверка статуса сервиса

```bash
# Статус Flask приложения
sudo systemctl status flask_app

# Перезапуск приложения
sudo systemctl restart flask_app

# Просмотр последних 50 строк логов после перезапуска
sudo journalctl -u flask_app -n 50 --no-pager
```

## Что искать в логах:

1. **`[UPDATE_TEACHER]`** - метки начала обновления
2. **Ошибки валидации** - проблемы с данными
3. **Ошибки БД** - проблемы с коммитом или запросами
4. **Traceback** - полный стек ошибок

## После проверки логов:

Если видите ошибки, скопируйте их и отправьте для анализа.

