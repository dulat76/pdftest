"""Настройка локальной БД для разработки (SQLite)."""
import os
import sys

# Создаем локальную БД SQLite для разработки
LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), 'local_dev.db')
LOCAL_DB_URL = f'sqlite:///{LOCAL_DB_PATH}'

print("=" * 60)
print("Настройка локальной БД для разработки")
print("=" * 60)

# Устанавливаем переменную окружения для использования SQLite
os.environ['DATABASE_URL'] = LOCAL_DB_URL
os.environ['DB_SCHEMA'] = 'public'

print(f"✅ Используется локальная БД: {LOCAL_DB_PATH}")
print()

# Теперь импортируем и инициализируем
from models import init_db, SessionLocal, User
from auth_utils import AuthManager
from werkzeug.security import generate_password_hash

try:
    # Инициализация БД
    init_db()
    print("✅ Таблицы БД созданы")
    
    # Создание супер-пользователя
    db = SessionLocal()
    auth_manager = AuthManager()
    
    username = 'baseke'
    password = 'changeme123'
    
    # Проверка существования
    user = auth_manager.get_user_by_username(username)
    
    if user:
        print(f"✅ Супер-пользователь '{username}' уже существует")
        # Сброс пароля на всякий случай
        user.password_hash = generate_password_hash(password)
        db.commit()
        print(f"✅ Пароль обновлен на '{password}'")
    else:
        print(f"Создание супер-пользователя '{username}'...")
        result = auth_manager.create_user(
            username=username,
            password=password,
            role='superuser',
            is_active=True,
            is_admin=True
        )
        
        if result['success']:
            print(f"✅ Супер-пользователь создан!")
        else:
            print(f"❌ Ошибка: {result.get('error')}")
            sys.exit(1)
    
    # Тест аутентификации
    result = auth_manager.authenticate_user(username, password)
    if result['success']:
        print(f"✅ Аутентификация работает!")
    else:
        print(f"❌ Ошибка аутентификации: {result.get('error')}")
        sys.exit(1)
    
    db.close()
    auth_manager.close()
    
    print()
    print("=" * 60)
    print("✅ ГОТОВО!")
    print("=" * 60)
    print(f"Логин: {username}")
    print(f"Пароль: {password}")
    print()
    print("⚠️  ВАЖНО: Для использования локальной БД добавьте в начало app.py:")
    print("   import os")
    print("   os.environ['DATABASE_URL'] = 'sqlite:///local_dev.db'")
    print("   (перед импортом models)")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)



