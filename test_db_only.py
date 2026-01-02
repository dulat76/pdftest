#!/usr/bin/env python3
import sys
import os

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

# Импортируем только SQLAlchemy напрямую
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://flask_user:flask_password123@localhost:5433/flask_db')

print(f"🔍 Тест подключения к БД: {DATABASE_URL.replace('flask_password123', '***')}\n")

try:
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

