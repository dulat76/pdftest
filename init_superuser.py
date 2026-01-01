"""Script to initialize superuser account."""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import SessionLocal, User, init_db
from auth_utils import AuthManager
from werkzeug.security import generate_password_hash
from datetime import datetime

SUPERUSER_USERNAME = 'baseke'


def init_superuser():
    """Initialize superuser account if it doesn't exist."""
    print("🔧 Инициализация супер-пользователя...")
    
    # Инициализация БД (создание таблиц, если их нет)
    try:
        init_db()
        print("✅ Таблицы БД проверены/созданы")
    except Exception as e:
        print(f"⚠️ Ошибка при инициализации БД: {e}")
        return False
    
    db = SessionLocal()
    auth_manager = AuthManager()
    
    try:
        # Проверка существования супер-пользователя
        existing_user = auth_manager.get_user_by_username(SUPERUSER_USERNAME)
        
        if existing_user:
            print(f"✅ Супер-пользователь '{SUPERUSER_USERNAME}' уже существует")
            print(f"   ID: {existing_user.id}")
            print(f"   Роль: {existing_user.role}")
            print(f"   Активен: {existing_user.is_active}")
            return True
        
        # Получение пароля из переменной окружения или использование дефолтного
        password = os.getenv('SUPERUSER_PASSWORD', 'changeme123')
        
        if password == 'changeme123':
            print("⚠️  Используется дефолтный пароль 'changeme123'")
            print("   Рекомендуется установить переменную окружения SUPERUSER_PASSWORD")
        
        # Создание супер-пользователя
        result = auth_manager.create_user(
            username=SUPERUSER_USERNAME,
            password=password,
            role='superuser',
            is_active=True,
            is_admin=True
        )
        
        if result['success']:
            print(f"✅ Супер-пользователь '{SUPERUSER_USERNAME}' успешно создан")
            print(f"   ID: {result['user_id']}")
            print(f"   Пароль: {password}")
            print("   ⚠️  Сохраните пароль в безопасном месте!")
            return True
        else:
            print(f"❌ Ошибка при создании супер-пользователя: {result.get('error')}")
            return False
    
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()
        auth_manager.close()


if __name__ == "__main__":
    success = init_superuser()
    sys.exit(0 if success else 1)




