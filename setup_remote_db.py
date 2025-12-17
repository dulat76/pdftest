"""
Скрипт для первоначальной настройки удаленной PostgreSQL БД
Создает схему pdftest_schema и настраивает права доступа
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
SCHEMA_NAME = os.getenv('DB_SCHEMA', 'pdftest_schema')

def setup_database():
    """Создание схемы и настройка прав доступа"""
    
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL не найден в .env файле")
        print("Пожалуйста, создайте .env файл с параметрами подключения")
        return False
    
    print(f"🔗 Подключение к базе данных...")
    print(f"   URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'скрыто'}")
    
    try:
        engine = create_engine(DATABASE_URL, echo=True)
        
        with engine.connect() as conn:
            # 1. Создание схемы
            print(f"\n📦 Создание схемы {SCHEMA_NAME}...")
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}"))
            conn.commit()
            print(f"✅ Схема {SCHEMA_NAME} создана")
            
            # 2. Проверка существования схемы
            print(f"\n🔍 Проверка схемы...")
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata "
                f"WHERE schema_name = '{SCHEMA_NAME}'"
            ))
            
            if result.fetchone():
                print(f"✅ Схема {SCHEMA_NAME} существует")
            else:
                print(f"❌ Ошибка: схема не найдена")
                return False
            
            # 3. Установка search_path для текущего пользователя
            db_user = os.getenv('DB_USER', 'n8n_user')
            print(f"\n🔧 Настройка search_path для пользователя {db_user}...")
            
            try:
                conn.execute(text(
                    f"ALTER USER {db_user} "
                    f"SET search_path TO {SCHEMA_NAME}, public"
                ))
                conn.commit()
                print(f"✅ search_path настроен")
            except Exception as e:
                print(f"⚠️  Предупреждение: не удалось установить search_path: {e}")
                print(f"   Это не критично, продолжаем...")
            
            # 4. Проверка прав доступа
            print(f"\n🔐 Проверка прав доступа...")
            result = conn.execute(text(
                f"SELECT has_schema_privilege('{db_user}', '{SCHEMA_NAME}', 'CREATE')"
            ))
            
            has_privilege = result.fetchone()[0]
            if has_privilege:
                print(f"✅ Пользователь {db_user} имеет права на схему {SCHEMA_NAME}")
            else:
                print(f"⚠️  Предупреждение: недостаточно прав на схему")
            
            # 5. Список существующих таблиц в схеме
            print(f"\n📋 Существующие таблицы в схеме {SCHEMA_NAME}:")
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = '{SCHEMA_NAME}'"
            ))
            
            tables = result.fetchall()
            if tables:
                for table in tables:
                    print(f"   - {table[0]}")
            else:
                print(f"   (пусто - таблицы будут созданы миграциями)")
        
        print(f"\n🎉 База данных успешно настроена!")
        print(f"\n📝 Следующие шаги:")
        print(f"   1. Создайте модели в models.py")
        print(f"   2. Создайте миграцию: alembic revision --autogenerate -m 'add multi-school models'")
        print(f"   3. Примените миграцию: alembic upgrade head")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка подключения к базе данных:")
        print(f"   {str(e)}")
        print(f"\n💡 Возможные причины:")
        print(f"   - Неверный IP адрес или порт")
        print(f"   - Firewall блокирует подключение")
        print(f"   - Неверные учетные данные")
        print(f"   - PostgreSQL не настроен для удаленных подключений")
        return False

def test_connection():
    """Простая проверка подключения к БД"""
    print("🧪 Тестирование подключения к базе данных...\n")
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL не найден в .env")
        return False
    
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Подключение успешно!")
            print(f"📊 PostgreSQL версия: {version[:50]}...")
            return True
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("  PostgreSQL Remote Database Setup")
    print("  Настройка удаленной базы данных для pdftest")
    print("=" * 60)
    print()
    
    # Сначала тестируем подключение
    if test_connection():
        print()
        # Затем настраиваем схему
        if setup_database():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print("\n💡 Проверьте параметры подключения в .env файле")
        sys.exit(1)
