import psycopg2
import os
from datetime import datetime, timedelta
import hashlib
import json

# Данные подключения из переменных окружения
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'flask_db'),
    'database': os.getenv('POSTGRES_DB', 'flask_db'),
    'user': os.getenv('POSTGRES_USER', 'flask_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'flask_password123'),
    'port': int(os.getenv('POSTGRES_PORT', 5432))
}

def create_connection():
    """Создание подключения к БД"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Успешное подключение к PostgreSQL")
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return None

def create_cache_table(conn):
    """Создание таблицы кэша"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS ai_response_cache (
        id SERIAL PRIMARY KEY,
        cache_key VARCHAR(255) UNIQUE NOT NULL,
        student_answer TEXT NOT NULL,
        correct_variants TEXT NOT NULL,
        question_context TEXT,
        ai_provider VARCHAR(50) NOT NULL,
        ai_model VARCHAR(100) NOT NULL,
        is_correct BOOLEAN NOT NULL,
        confidence FLOAT NOT NULL,
        explanation TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        expires_at TIMESTAMP NOT NULL,
        usage_count INTEGER DEFAULT 1
    );
    """
    
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_cache_key ON ai_response_cache(cache_key);",
        "CREATE INDEX IF NOT EXISTS idx_expires_at ON ai_response_cache(expires_at);",
        "CREATE INDEX IF NOT EXISTS idx_created_at ON ai_response_cache(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_provider_model ON ai_response_cache(ai_provider, ai_model);"
    ]
    
    try:
        cursor = conn.cursor()
        
        # Создаем таблицу
        cursor.execute(create_table_sql)
        print("✅ Таблица ai_response_cache создана/проверена")
        
        # Создаем индексы
        for index_sql in create_indexes_sql:
            cursor.execute(index_sql)
        print("✅ Индексы созданы/проверены")
        
        conn.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания таблицы: {e}")
        conn.rollback()
        return False

def generate_cache_key(student_answer, correct_variants, question_context, ai_model):
    """Генерация ключа кэша"""
    data = f"{student_answer}_{json.dumps(correct_variants, sort_keys=True)}_{question_context}_{ai_model}"
    return hashlib.md5(data.encode('utf-8')).hexdigest()

def test_cache_operations(conn):
    """Тестирование операций с кэшем"""
    print("\n🧪 Тестирование операций с кэшем...")
    
    try:
        cursor = conn.cursor()
        
        # 1. Вставка тестовой записи
        test_data = {
            'cache_key': generate_cache_key('Астана', ['Астана', 'Нур-Султан'], 'Столица Казахстана', 'gemini-pro'),
            'student_answer': 'Астана',
            'correct_variants': json.dumps(['Астана', 'Нур-Султан']),
            'question_context': 'Столица Казахстана',
            'ai_provider': 'gemini',
            'ai_model': 'gemini-pro',
            'is_correct': True,
            'confidence': 0.95,
            'explanation': 'Ответ верный, столица Казахстана - Астана',
            'expires_at': datetime.now() + timedelta(hours=1)  # ИСПРАВЛЕНО: datetime.now()
        }
        
        insert_sql = """
        INSERT INTO ai_response_cache 
        (cache_key, student_answer, correct_variants, question_context, ai_provider, ai_model, is_correct, confidence, explanation, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_sql, (
            test_data['cache_key'],
            test_data['student_answer'],
            test_data['correct_variants'],
            test_data['question_context'],
            test_data['ai_provider'],
            test_data['ai_model'],
            test_data['is_correct'],
            test_data['confidence'],
            test_data['explanation'],
            test_data['expires_at']
        ))
        print("✅ Тестовая запись добавлена")
        
        # 2. Проверка чтения
        cursor.execute("SELECT * FROM ai_response_cache WHERE cache_key = %s", (test_data['cache_key'],))
        result = cursor.fetchone()
        if result:
            print(f"✅ Запись найдена: ID={result[0]}, Ответ={result[2]}")
        else:
            print("❌ Запись не найдена")
        
        # 3. Проверка TTL
        cursor.execute("SELECT COUNT(*) FROM ai_response_cache WHERE expires_at > NOW()")
        valid_count = cursor.fetchone()[0]
        print(f"✅ Действительных записей: {valid_count}")
        
        # 4. Вставка устаревшей записи
        expired_key = generate_cache_key('Москва', ['Москва'], 'Столица России', 'gemini-pro')
        cursor.execute(insert_sql, (
            expired_key,
            'Москва',
            json.dumps(['Москва']),
            'Столица России',
            'gemini',
            'gemini-pro',
            True,
            0.90,
            'Правильный ответ',
            datetime.now() - timedelta(hours=1)  # ИСПРАВЛЕНО: datetime.now()
        ))
        print("✅ Устаревшая запись добавлена")
        
        # 5. Проверка TTL фильтрации
        cursor.execute("SELECT COUNT(*) FROM ai_response_cache WHERE cache_key = %s AND expires_at > NOW()", (expired_key,))
        expired_valid = cursor.fetchone()[0]
        print(f"✅ Устаревших записей в выборке: {expired_valid} (должно быть 0)")
        
        # 6. Очистка устаревших записей
        cursor.execute("DELETE FROM ai_response_cache WHERE expires_at < NOW()")
        deleted_count = cursor.rowcount
        print(f"✅ Удалено устаревших записей: {deleted_count}")
        
        # 7. Статистика
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(confidence) as avg_confidence,
                COUNT(DISTINCT ai_provider) as providers
            FROM ai_response_cache
        """)
        stats = cursor.fetchone()
        print(f"📊 Статистика: записей={stats[0]}, ср. уверенность={stats[1]:.2f}, провайдеров={stats[2]}")
        
        conn.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        conn.rollback()
        return False

def cleanup_test_data(conn):
    """Очистка тестовых данных"""
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ai_response_cache WHERE student_answer IN ('Астана', 'Москва')")
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()
        print(f"🧹 Очищено тестовых записей: {deleted}")
    except Exception as e:
        print(f"⚠️ Ошибка очистки: {e}")

def main():
    """Основная функция"""
    print("🚀 Инициализация кэша в PostgreSQL")
    
    # Подключаемся к БД
    conn = create_connection()
    if not conn:
        return
    
    try:
        # Создаем таблицу
        if not create_cache_table(conn):
            return
        
        # Тестируем операции
        if not test_cache_operations(conn):
            return
        
        # Очищаем тестовые данные
        cleanup_test_data(conn)
        
        print("\n🎉 Все тесты пройдены успешно! Таблица готова к использованию.")
        
    finally:
        conn.close()
        print("🔌 Подключение закрыто")

if __name__ == "__main__":
    main()