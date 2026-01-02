#!/usr/bin/env python3
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Пытаемся загрузить из models.py (там уже есть dotenv)
try:
    from models import engine, SessionLocal
    DATABASE_URL = str(engine.url)
    print("✅ Используем DATABASE_URL из models.py")
except:
    # Если не получилось, используем прямое подключение
    try:
        from dotenv import load_dotenv
        load_dotenv()
        DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://flask_user:flask_password123@localhost:5433/flask_db')
    except:
        DATABASE_URL = 'postgresql://flask_user:flask_password123@localhost:5433/flask_db'

# Импортируем только SQLAlchemy напрямую
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Если не получили из models, создаем engine заново
try:
    if 'engine' not in locals():
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
except:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

print(f"🔍 Тест подключения к БД: {DATABASE_URL.replace('flask_password123', '***')}\n")

try:
    # Используем уже созданные engine и SessionLocal, или создаем новые
    if 'engine' not in locals() or 'SessionLocal' not in locals():
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
    
    db = SessionLocal()
    
    # Проверка подключения
    result = db.execute(text("SELECT 1"))
    print("✅ Подключение к БД успешно\n")
    
    # Получение пользователей
    result = db.execute(text("""
        SELECT id, username, email, role, city, school, is_active, 
               LENGTH(password_hash) as hash_length,
               LEFT(password_hash, 20) as hash_start
        FROM users
        ORDER BY id
    """))
    
    users = result.fetchall()
    print(f"📊 Найдено пользователей: {len(users)}\n")
    
    for user in users:
        print(f"👤 Пользователь: {user.username}")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email or 'не указан'}")
        print(f"   Роль: {user.role}")
        print(f"   Город: {user.city or 'не указан'}")
        print(f"   Школа: {user.school or 'не указана'}")
        print(f"   Активен: {'Да' if user.is_active else 'Нет'}")
        print(f"   Хеш пароля: длина={user.hash_length}, начало={user.hash_start}")
        print("-" * 60)
    
    db.close()
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

