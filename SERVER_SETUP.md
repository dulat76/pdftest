# 🔧 Настройка PostgreSQL сервера для удаленного доступа

## Проблема
```
❌ Connection timed out
Is the server running on that host and accepting TCP/IP connections?
```

Это означает, что PostgreSQL на сервере **185.22.64.9** не принимает удаленные подключения.

---

## Решение: Настройка сервера (выполнить на сервере)

### Шаг 1: Подключитесь к серверу по SSH

```bash
ssh root@185.22.64.9
# или
ssh your_username@185.22.64.9
```

### Шаг 2: Проверьте, запущен ли PostgreSQL

```bash
sudo systemctl status postgresql
```

Если не запущен:
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Шаг 3: Настройте PostgreSQL для удаленных подключений

#### 3.1. Найдите конфигурационный файл

```bash
sudo -u postgres psql -c "SHOW config_file;"
```

Обычно это:
- Ubuntu/Debian: `/etc/postgresql/14/main/postgresql.conf`
- CentOS/RHEL: `/var/lib/pgsql/14/data/postgresql.conf`

#### 3.2. Отредактируйте `postgresql.conf`

```bash
sudo nano /etc/postgresql/14/main/postgresql.conf
```

Найдите строку `listen_addresses` и измените на:
```conf
listen_addresses = '*'
```

Или для безопасности (только ваш IP):
```conf
listen_addresses = 'localhost,185.22.64.9'
```

#### 3.3. Настройте `pg_hba.conf` для аутентификации

```bash
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Добавьте в конец файла:
```conf
# Allow remote connections from anywhere (для разработки)
host    flask_db    flask_user    0.0.0.0/0    md5

# Или только с вашего IP (безопаснее)
host    flask_db    flask_user    YOUR_LOCAL_IP/32    md5
```

**Пример**:
```conf
# IPv4 remote connections
host    flask_db    flask_user    0.0.0.0/0    md5
host    all         all           0.0.0.0/0    md5
```

### Шаг 4: Перезапустите PostgreSQL

```bash
sudo systemctl restart postgresql
```

Проверьте статус:
```bash
sudo systemctl status postgresql
```

### Шаг 5: Настройте Firewall

#### Для UFW (Ubuntu/Debian):
```bash
# Проверить статус
sudo ufw status

# Открыть порт 5432
sudo ufw allow 5432/tcp

# Или только с вашего IP
sudo ufw allow from YOUR_LOCAL_IP to any port 5432

# Применить изменения
sudo ufw reload
```

#### Для firewalld (CentOS/RHEL):
```bash
# Открыть порт
sudo firewall-cmd --permanent --add-port=5432/tcp

# Перезагрузить firewall
sudo firewall-cmd --reload

# Проверить
sudo firewall-cmd --list-ports
```

#### Для iptables:
```bash
sudo iptables -A INPUT -p tcp --dport 5432 -j ACCEPT
sudo iptables-save
```

### Шаг 6: Проверьте, слушает ли PostgreSQL на всех интерфейсах

```bash
sudo netstat -tuln | grep 5432
```

Должно быть:
```
tcp        0      0 0.0.0.0:5432            0.0.0.0:*               LISTEN
```

Если видите `127.0.0.1:5432` - значит PostgreSQL слушает только localhost.

---

## Проверка с локального компьютера

После настройки сервера, проверьте подключение:

### Вариант 1: Через telnet
```bash
telnet 185.22.64.9 5432
```

Если подключается - увидите что-то вроде:
```
Trying 185.22.64.9...
Connected to 185.22.64.9.
```

### Вариант 2: Через psql (если установлен)
```bash
psql -h 185.22.64.9 -U flask_user -d flask_db
```

Введите пароль: `flask_password123`

### Вариант 3: Через наш скрипт
```bash
python setup_remote_db.py
```

Должно быть:
```
✅ Подключение успешно!
📊 PostgreSQL версия: ...
```

---

## Альтернативное решение: SSH Туннель

Если не можете открыть порт 5432 напрямую, используйте SSH туннель:

### На локальном компьютере:

```bash
ssh -L 5432:localhost:5432 root@185.22.64.9 -N
```

Затем в `.env` измените:
```env
DB_HOST=localhost
DATABASE_URL=postgresql://flask_user:flask_password123@localhost:5432/flask_db
```

---

## Безопасность

> [!WARNING]
> **Важно для production!**

После тестирования рекомендуется:

1. **Ограничить доступ по IP**:
```conf
# В pg_hba.conf
host    flask_db    flask_user    YOUR_IP/32    md5
```

2. **Использовать SSL**:
```conf
# В postgresql.conf
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
```

3. **Изменить пароль на более сложный**:
```sql
ALTER USER flask_user WITH PASSWORD 'very_secure_password_here_123!@#';
```

4. **Использовать fail2ban** для защиты от брутфорса:
```bash
sudo apt install fail2ban
```

---

## Чеклист настройки сервера

- [ ] PostgreSQL запущен и работает
- [ ] `postgresql.conf`: `listen_addresses = '*'`
- [ ] `pg_hba.conf`: добавлена строка для flask_user
- [ ] PostgreSQL перезапущен
- [ ] Firewall открыт для порта 5432
- [ ] Проверка через telnet успешна
- [ ] Проверка через setup_remote_db.py успешна

---

## Что делать дальше?

После успешного подключения:

1. ✅ Создать модели для мультишкольной системы
2. ✅ Создать миграции Alembic
3. ✅ Применить миграции
4. ✅ Начать разработку

**Нужна помощь с настройкой сервера?** Я могу подготовить готовый скрипт для автоматической настройки! 🚀
