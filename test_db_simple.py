#!/usr/bin/env python3
"""
Простой скрипт для проверки БД без зависимостей
Использует только psycopg2 или стандартные библиотеки
"""
import sys
import os

# Пытаемся использовать psycopg2 напрямую
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    # Параметры подключения (можно изменить)
    DB_CONFIG = {
        'host': 'localhost',
        'port': 5433,
        'database': 'flask_db',
        'user': 'flask_user',
        'password': 'flask_password123'
    }
    
    print(f"🔍 Подключение к БД: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}\n")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Проверка подключения
    cur.execute("SELECT 1")
    print("✅ Подключение к БД успешно\n")
    
    # Получение пользователей
    cur.execute("""
        SELECT 
            id, 
            username, 
            email, 
            role, 
            city, 
            school, 
            is_active,
            expiration_date,
            LENGTH(password_hash) as hash_length,
            LEFT(password_hash, 20) as hash_start
        FROM users
        ORDER BY id
    """)
    
    users = cur.fetchall()
    print(f"📊 Найдено пользователей: {len(users)}\n")
    
    from datetime import date
    today = date.today()
    
    for user in users:
        print(f"👤 Пользователь: {user['username']}")
        print(f"   ID: {user['id']}")
        print(f"   Email: {user['email'] or 'не указан'}")
        print(f"   Роль: {user['role']}")
        print(f"   Город: {user['city'] or 'не указан'}")
        print(f"   Школа: {user['school'] or 'не указана'}")
        print(f"   Активен: {'✅ Да' if user['is_active'] else '❌ Нет'}")
        
        if user['expiration_date']:
            exp_date = user['expiration_date']
            if today > exp_date:
                print(f"   ⚠️  Срок действия ИСТЕК: {exp_date}")
            else:
                days_left = (exp_date - today).days
                print(f"   Срок действия: {exp_date} (осталось {days_left} дн.)")
        else:
            print(f"   Срок действия: ✅ Бессрочно")
        
        print(f"   Хеш пароля: длина={user['hash_length']}, начало={user['hash_start']}")
        
        # Проверка формата хеша
        hash_start = user['hash_start']
        if hash_start.startswith('pbkdf2:sha256:'):
            print(f"   ✅ Формат хеша: pbkdf2:sha256 (правильный)")
        elif hash_start.startswith('$2b$') or hash_start.startswith('$2a$'):
            print(f"   ⚠️  Формат хеша: bcrypt")
        else:
            print(f"   ⚠️  Неизвестный формат хеша")
        
        print("-" * 60)
    
    cur.close()
    conn.close()
    
    print("\n✅ Проверка завершена")
    
except ImportError:
    print("❌ psycopg2 не установлен")
    print("Установите: pip install psycopg2-binary")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

