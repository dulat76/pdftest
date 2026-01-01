# Инструкция по исправлению прав доступа для templates_json

## Проблема
Ошибка: `[Errno 13] Permission denied: '/home/ubuntu/predmet_kz/flask_app/templates_json/tpl_*.json'`

## Решение

### Вариант 1: Изменить владельца директории (рекомендуется)

```bash
# Узнать, под каким пользователем запущен Flask
sudo systemctl status flask_app | grep "Main PID"

# Обычно это пользователь ubuntu или root
# Изменить владельца директории на пользователя, под которым запущен Flask
sudo chown -R ubuntu:ubuntu /home/ubuntu/predmet_kz/flask_app/templates_json
sudo chown -R ubuntu:ubuntu /home/ubuntu/predmet_kz/flask_app/uploads

# Установить права доступа
sudo chmod -R 755 /home/ubuntu/predmet_kz/flask_app/templates_json
sudo chmod -R 755 /home/ubuntu/predmet_kz/flask_app/uploads
```

### Вариант 2: Изменить права доступа для всех

```bash
# Установить права на запись для всех (менее безопасно)
sudo chmod -R 777 /home/ubuntu/predmet_kz/flask_app/templates_json
sudo chmod -R 777 /home/ubuntu/predmet_kz/flask_app/uploads
```

### Вариант 3: Проверить systemd unit файл

```bash
# Проверить, под каким пользователем запущен Flask
cat /etc/systemd/system/flask_app.service | grep User

# Если User не указан, добавить в файл:
# User=ubuntu
# Group=ubuntu

# После изменения перезагрузить systemd и перезапустить сервис
sudo systemctl daemon-reload
sudo systemctl restart flask_app
```

### Проверка

```bash
# Проверить права доступа
ls -la /home/ubuntu/predmet_kz/flask_app/templates_json
ls -la /home/ubuntu/predmet_kz/flask_app/uploads

# Проверить, может ли пользователь писать в директорию
sudo -u ubuntu touch /home/ubuntu/predmet_kz/flask_app/templates_json/test.txt
sudo -u ubuntu rm /home/ubuntu/predmet_kz/flask_app/templates_json/test.txt
```

### После исправления

```bash
# Перезапустить Flask приложение
sudo systemctl restart flask_app

# Проверить логи
sudo journalctl -u flask_app -n 50 --no-pager
```

