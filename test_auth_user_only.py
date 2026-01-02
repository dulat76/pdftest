#!/usr/bin/env python3
"""
Упрощенный скрипт для диагностики аутентификации
Импортирует только User модель, чтобы избежать проблем с другими моделями
"""
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🔍 Диагностика проблемы аутентификации (только User модель)...\n")

# Импортируем только необходимое
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from datetime import datetime, date

# Загружаем DATABASE_URL
from dotenv import load_dotenv
load_dotenv()
import os as os_module

DATABASE_URL = os_module.getenv('DATABASE_URL', 'postgresql://flask_user:flask_password123@localhost:5433/flask_db')

# Создаем упрощенную модель User только для этого скрипта
Base = declarative_base()

class UserSimple(Base):
    """Упрощенная модель User только для диагностики."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default='teacher', index=True)
    city = Column(String(100), nullable=True)
    city_code = Column(String(20), nullable=True)
    school = Column(String(200), nullable=True)
    school_code = Column(String(50), nullable=True)
    expiration_date = Column(Date, nullable=True)
    max_tests_limit = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

# Создаем engine и session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# 1. Проверка подключения к БД
print("1️⃣ Проверка подключения к БД...")
try:
    print(f"   ✅ DATABASE_URL: {str(engine.url).replace('flask_password123', '***')}")
    
    db = SessionLocal()
    db.execute(text("SELECT 1"))
    print("   ✅ Подключение к БД успешно")
    db.close()
except Exception as e:
    print(f"   ❌ Ошибка подключения: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. Проверка пользователей
print("\n2️⃣ Проверка пользователей в БД...")
try:
    db = SessionLocal()
    users = db.query(UserSimple).all()
    print(f"   ✅ Найдено пользователей: {len(users)}")
    
    for user in users:
        print(f"\n   👤 Пользователь: {user.username}")
        print(f"      ID: {user.id}")
        print(f"      Роль: {user.role}")
        print(f"      Активен: {user.is_active}")
        if user.password_hash:
            print(f"      Пароль (хеш): {user.password_hash[:50]}...")
            print(f"      Длина хеша: {len(user.password_hash)}")
            
            # Проверка формата хеша
            if user.password_hash.startswith('pbkdf2:sha256:'):
                print(f"      ✅ Формат хеша: pbkdf2:sha256 (правильный)")
            elif user.password_hash.startswith('$2b$') or user.password_hash.startswith('$2a$'):
                print(f"      ⚠️  Формат хеша: bcrypt")
            else:
                print(f"      ⚠️  Неизвестный формат хеша: {user.password_hash[:20]}")
        else:
            print(f"      ❌ ХЕШ ПАРОЛЯ ОТСУТСТВУЕТ!")
    
    db.close()
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

# 3. Тест функции authenticate_user
print("\n3️⃣ Тест функции authenticate_user...")
try:
    # Импортируем auth_utils - он использует полную модель User из models.py
    # Но мы можем протестировать логику напрямую
    from werkzeug.security import check_password_hash
    
    db = SessionLocal()
    users = db.query(UserSimple).all()
    
    for user in users:
        print(f"\n   Тестирую пользователя: {user.username}")
        
        # Проверяем пароль напрямую
        print(f"      Проверка с неправильным паролем...")
        try:
            result = check_password_hash(user.password_hash, "wrong_password")
            print(f"      Результат проверки: {result} (ожидается False)")
        except Exception as e:
            print(f"      ❌ Ошибка при проверке пароля: {e}")
            import traceback
            traceback.print_exc()
    
    db.close()
    
    # Теперь попробуем через auth_manager
    print(f"\n   Тестирую через auth_manager.authenticate_user...")
    try:
        # Импортируем только auth_manager, но это может вызвать проблему с моделями
        # Поэтому попробуем обойти проблему
        import importlib.util
        spec = importlib.util.spec_from_file_location("auth_utils", "auth_utils.py")
        if spec and spec.loader:
            # Временно отключим проблемную модель
            import sys
            original_import = __builtins__.__import__
            
            def selective_import(name, *args, **kwargs):
                if name == 'models' and 'Subject' in str(args):
                    # Пропускаем проблемный импорт
                    pass
                return original_import(name, *args, **kwargs)
            
            # Это сложно, лучше просто протестируем напрямую
            print("      ⚠️  Пропускаем тест через auth_manager из-за проблем с моделями")
    except Exception as e:
        print(f"      ⚠️  Не удалось протестировать через auth_manager: {e}")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ Диагностика завершена")
print("="*80)
print("\n💡 Для полного теста auth_manager нужно исправить relationship в models.py")

