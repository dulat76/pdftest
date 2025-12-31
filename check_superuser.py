"""Скрипт для проверки и создания супер-пользователя."""
import sys
import os

# Устанавливаем локальную SQLite БД по умолчанию
default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'local_dev.db')
os.environ.setdefault('DATABASE_URL', f'sqlite:///{default_db}')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import SessionLocal, User, init_db
from auth_utils import AuthManager
from werkzeug.security import check_password_hash, generate_password_hash

def check_and_create_superuser():
    """Проверка и создание супер-пользователя."""
    print("=" * 60)
    print("Проверка супер-пользователя")
    print("=" * 60)
    
    # Инициализация БД
    try:
        init_db()
        print("✅ Таблицы БД проверены/созданы")
    except Exception as e:
        print(f"❌ Ошибка при инициализации БД: {e}")
        return False
    
    db = SessionLocal()
    auth_manager = AuthManager()
    
    try:
        username = 'baseke'
        password = 'changeme123'
        
        # Проверка существования
        user = auth_manager.get_user_by_username(username)
        
        if user:
            print(f"\n✅ Пользователь '{username}' найден в БД")
            print(f"   ID: {user.id}")
            print(f"   Роль: {user.role}")
            print(f"   Активен: {user.is_active}")
            print(f"   is_admin: {user.is_admin}")
            
            # Проверка пароля
            if check_password_hash(user.password_hash, password):
                print(f"   ✅ Пароль 'changeme123' правильный!")
            else:
                print(f"   ❌ Пароль 'changeme123' НЕ подходит")
                print(f"   Хеш пароля в БД: {user.password_hash[:50]}...")
                
                # Предложение сбросить пароль
                print("\n💡 Хотите сбросить пароль на 'changeme123'? (y/n): ", end='')
                response = input().strip().lower()
                if response == 'y':
                    user.password_hash = generate_password_hash(password)
                    db.commit()
                    print("   ✅ Пароль сброшен на 'changeme123'")
                else:
                    print("   Пароль не изменен")
        else:
            print(f"\n❌ Пользователь '{username}' НЕ найден в БД")
            print("\nСоздание супер-пользователя...")
            
            result = auth_manager.create_user(
                username=username,
                password=password,
                role='superuser',
                is_active=True,
                is_admin=True
            )
            
            if result['success']:
                print(f"✅ Супер-пользователь '{username}' создан!")
                print(f"   Логин: {username}")
                print(f"   Пароль: {password}")
            else:
                print(f"❌ Ошибка создания: {result.get('error')}")
                return False
        
        # Тест аутентификации
        print("\n" + "=" * 60)
        print("Тест аутентификации")
        print("=" * 60)
        result = auth_manager.authenticate_user(username, password)
        
        if result['success']:
            print(f"✅ Аутентификация успешна!")
            print(f"   Логин: {result['login']}")
            print(f"   Роль: {result['role']}")
            print(f"   User ID: {result['user_id']}")
        else:
            print(f"❌ Ошибка аутентификации: {result.get('error')}")
            return False
        
        return True
    
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()
        auth_manager.close()

if __name__ == "__main__":
    success = check_and_create_superuser()
    if success:
        print("\n" + "=" * 60)
        print("✅ ВСЕ ОК! Можете войти с:")
        print("   Логин: baseke")
        print("   Пароль: changeme123")
        print("=" * 60)
    else:
        print("\n❌ Есть проблемы. Проверьте ошибки выше.")
    sys.exit(0 if success else 1)

