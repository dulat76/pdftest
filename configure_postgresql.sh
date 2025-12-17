#!/bin/bash
# Автоматическая настройка PostgreSQL для удаленного доступа
# Запускать на сервере: sudo bash configure_postgresql.sh

set -e  # Остановка при ошибке

echo "=================================================="
echo "  PostgreSQL Remote Access Configuration"
echo "  Настройка удаленного доступа к PostgreSQL"
echo "=================================================="
echo ""

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Пожалуйста, запустите скрипт с правами root:"
    echo "   sudo bash configure_postgresql.sh"
    exit 1
fi

# Определение версии PostgreSQL
PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
echo "📊 Обнаружена PostgreSQL версия: $PG_VERSION"

# Определение пути к конфигурационным файлам
if [ -d "/etc/postgresql/$PG_VERSION/main" ]; then
    PG_CONF_DIR="/etc/postgresql/$PG_VERSION/main"
elif [ -d "/var/lib/pgsql/$PG_VERSION/data" ]; then
    PG_CONF_DIR="/var/lib/pgsql/$PG_VERSION/data"
else
    echo "❌ Не удалось найти конфигурационные файлы PostgreSQL"
    exit 1
fi

echo "📁 Конфигурационная директория: $PG_CONF_DIR"
echo ""

# Бэкап конфигурационных файлов
echo "💾 Создание бэкапов конфигурационных файлов..."
cp "$PG_CONF_DIR/postgresql.conf" "$PG_CONF_DIR/postgresql.conf.backup.$(date +%Y%m%d_%H%M%S)"
cp "$PG_CONF_DIR/pg_hba.conf" "$PG_CONF_DIR/pg_hba.conf.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ Бэкапы созданы"
echo ""

# Настройка postgresql.conf
echo "🔧 Настройка postgresql.conf..."
if grep -q "^listen_addresses" "$PG_CONF_DIR/postgresql.conf"; then
    sed -i "s/^listen_addresses.*/listen_addresses = '*'/" "$PG_CONF_DIR/postgresql.conf"
else
    echo "listen_addresses = '*'" >> "$PG_CONF_DIR/postgresql.conf"
fi
echo "✅ listen_addresses = '*' установлен"
echo ""

# Настройка pg_hba.conf
echo "🔧 Настройка pg_hba.conf..."
if ! grep -q "host.*flask_db.*flask_user" "$PG_CONF_DIR/pg_hba.conf"; then
    echo "" >> "$PG_CONF_DIR/pg_hba.conf"
    echo "# Remote access for pdftest application" >> "$PG_CONF_DIR/pg_hba.conf"
    echo "host    flask_db    flask_user    0.0.0.0/0    md5" >> "$PG_CONF_DIR/pg_hba.conf"
    echo "host    all         all           0.0.0.0/0    md5" >> "$PG_CONF_DIR/pg_hba.conf"
    echo "✅ Правила доступа добавлены"
else
    echo "⚠️  Правила уже существуют, пропускаем"
fi
echo ""

# Перезапуск PostgreSQL
echo "🔄 Перезапуск PostgreSQL..."
systemctl restart postgresql
sleep 2

if systemctl is-active --quiet postgresql; then
    echo "✅ PostgreSQL успешно перезапущен"
else
    echo "❌ Ошибка перезапуска PostgreSQL"
    systemctl status postgresql
    exit 1
fi
echo ""

# Настройка Firewall
echo "🔥 Настройка Firewall..."

# UFW (Ubuntu/Debian)
if command -v ufw &> /dev/null; then
    echo "   Обнаружен UFW"
    ufw allow 5432/tcp
    ufw reload
    echo "✅ UFW: порт 5432 открыт"
fi

# firewalld (CentOS/RHEL)
if command -v firewall-cmd &> /dev/null; then
    echo "   Обнаружен firewalld"
    firewall-cmd --permanent --add-port=5432/tcp
    firewall-cmd --reload
    echo "✅ firewalld: порт 5432 открыт"
fi

# iptables (если нет UFW и firewalld)
if ! command -v ufw &> /dev/null && ! command -v firewall-cmd &> /dev/null; then
    echo "   Используем iptables"
    iptables -A INPUT -p tcp --dport 5432 -j ACCEPT
    iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
    echo "✅ iptables: порт 5432 открыт"
fi
echo ""

# Проверка, слушает ли PostgreSQL на всех интерфейсах
echo "🔍 Проверка сетевых настроек..."
if netstat -tuln | grep -q "0.0.0.0:5432"; then
    echo "✅ PostgreSQL слушает на всех интерфейсах (0.0.0.0:5432)"
elif netstat -tuln | grep -q "127.0.0.1:5432"; then
    echo "⚠️  PostgreSQL слушает только на localhost"
    echo "   Возможно, требуется дополнительная настройка"
else
    echo "❌ PostgreSQL не слушает на порту 5432"
fi
echo ""

# Проверка существования БД и пользователя
echo "🔍 Проверка базы данных и пользователя..."
su - postgres -c "psql -c \"SELECT 1 FROM pg_database WHERE datname='flask_db'\"" | grep -q 1 && \
    echo "✅ База данных flask_db существует" || \
    echo "⚠️  База данных flask_db не найдена (создайте через flask_init.sql)"

su - postgres -c "psql -c \"SELECT 1 FROM pg_roles WHERE rolname='flask_user'\"" | grep -q 1 && \
    echo "✅ Пользователь flask_user существует" || \
    echo "⚠️  Пользователь flask_user не найден (создайте через flask_init.sql)"
echo ""

# Итоговая информация
echo "=================================================="
echo "  ✅ Настройка завершена!"
echo "=================================================="
echo ""
echo "📝 Следующие шаги:"
echo "   1. Проверьте подключение с локального компьютера:"
echo "      telnet 185.22.64.9 5432"
echo ""
echo "   2. Или через psql:"
echo "      psql -h 185.22.64.9 -U flask_user -d flask_db"
echo ""
echo "   3. Или через Python скрипт:"
echo "      python setup_remote_db.py"
echo ""
echo "🔒 Для production рекомендуется:"
echo "   - Ограничить доступ по IP в pg_hba.conf"
echo "   - Включить SSL соединения"
echo "   - Изменить пароль на более сложный"
echo "   - Установить fail2ban для защиты от брутфорса"
echo ""
echo "📋 Бэкапы конфигурационных файлов сохранены в:"
echo "   $PG_CONF_DIR/*.backup.*"
echo ""
