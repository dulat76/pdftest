#!/usr/bin/env python3
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Пытаемся импортировать werkzeug
try:
    from werkzeug.security import check_password_hash
except ImportError:
    print("⚠️  werkzeug не найден, проверка паролей будет пропущена")
    def check_password_hash(pwhash, password):
        return False

print("🔍 Диагностика проблемы аутентификации...\n")

# 1. Проверка подключения к БД
print("1️⃣ Проверка подключения к БД...")
try:
    # Импортируем только модели, без app.py
    from models import SessionLocal, User, engine
    print(f"   ✅ DATABASE_URL: {str(engine.url).replace('flask_password123', '***')}")
    
    db = SessionLocal()
    db.execute("SELECT 1")
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
    users = db.query(User).all()
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
    # Импортируем auth_utils напрямую
    from auth_utils import auth_manager
    
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    
    for user in users:
        print(f"\n   Тестирую пользователя: {user.username}")
        
        # Попробуем с неправильным паролем
        print(f"      Вызываю authenticate_user с неправильным паролем...")
        try:
            result = auth_manager.authenticate_user(user.username, "wrong_password")
            print(f"      Результат: {result}")
        except Exception as e:
            print(f"      ❌ ИСКЛЮЧЕНИЕ при вызове: {e}")
            import traceback
            traceback.print_exc()
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

# 4. Проверка логики проверки пароля напрямую
print("\n4️⃣ Проверка проверки пароля напрямую...")
try:
    db = SessionLocal()
    users = db.query(User).all()
    
    for user in users:
        print(f"\n   Пользователь: {user.username}")
        
        if not user.password_hash:
            print(f"      ❌ ХЕШ ПАРОЛЯ ПУСТОЙ!")
            continue
            
        print(f"      Хеш пароля (первые 50 символов): {user.password_hash[:50]}...")
        
        # Попробуем проверить с неправильным паролем
        try:
            result = check_password_hash(user.password_hash, "wrong_password")
            print(f"      Проверка с неправильным паролем: {result} (ожидается False)")
        except Exception as e:
            print(f"      ❌ Ошибка при проверке пароля: {e}")
            import traceback
            traceback.print_exc()
    
    db.close()
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ Диагностика завершена")
print("="*80)

