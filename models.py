"""Database models using SQLAlchemy."""
from datetime import datetime, date
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, Date, JSON, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL from environment
# По умолчанию используем PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://flask_user:flask_password123@185.22.64.9:5432/flask_db')
DB_SCHEMA = os.getenv('DB_SCHEMA', 'public')

# Create engine with connection pooling
# Для SQLite используем другие настройки
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
else:
    # Для PostgreSQL
    connect_args = {}
    if DB_SCHEMA != 'public':
        connect_args["options"] = f"-c search_path={DB_SCHEMA},public"
    
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
        connect_args=connect_args
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class User(Base):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Поля ФИО
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Новые поля для учителей
    role = Column(String(20), nullable=False, default='teacher', index=True)  # 'superuser' или 'teacher'
    city = Column(String(100), nullable=True)
    city_code = Column(String(20), nullable=True)
    school = Column(String(200), nullable=True)
    school_code = Column(String(50), nullable=True)
    expiration_date = Column(Date, nullable=True)
    max_tests_limit = Column(Integer, nullable=True)  # Лимит на количество тестов
    ai_checking_enabled = Column(Boolean, default=False, nullable=False)  # Индивидуальная настройка ИИ проверки
    
    # Поля для выбора AI модели
    ai_model_id = Column(Integer, ForeignKey('ai_models.id', ondelete='SET NULL'), nullable=True, index=True)  # Выбранная модель
    ai_api_key = Column(String(500), nullable=True)  # API ключ для внешних моделей
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship к AI модели
    ai_model = relationship('AIModel', foreign_keys=[ai_model_id])


class Template(Base):
    """Template model for storing test templates."""
    __tablename__ = 'templates'
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    fields = Column(JSON, nullable=False)  # Store fields as JSON
    images = Column(JSON, nullable=True)   # Store image references
    created_by = Column(Integer, nullable=True)  # Foreign key to users
    
    # Новые поля для уникальных ссылок
    topic = Column(String(200), nullable=True)  # Название темы теста
    created_by_username = Column(String(100), nullable=True, index=True)  # Логин учителя
    topic_slug = Column(String(200), nullable=True)  # URL-friendly версия темы
    is_public = Column(Boolean, default=True)  # Публичный ли тест
    access_count = Column(Integer, default=0)  # Количество прохождений
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    
    # Новые поля для класса и предмета
    class_number = Column(Integer, nullable=True)  # Класс (1-11)
    subject_id = Column(Integer, nullable=True, index=True)  # Foreign key to subjects
    
    # Уникальный индекс на (created_by_username, subject_id, topic_slug)
    __table_args__ = (
        Index('idx_username_subject_topic', 'created_by_username', 'subject_id', 'topic_slug', unique=True),
    )


class Subject(Base):
    """Subject model for school subjects."""
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)  # Название предмета
    name_slug = Column(String(200), nullable=False, unique=True, index=True)  # URL-friendly версия
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship для доступа к классам (будет установлено после определения SubjectClass)


class SubjectClass(Base):
    """Many-to-many relationship between subjects and classes."""
    __tablename__ = 'subject_classes'
    
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False, index=True)
    class_number = Column(Integer, nullable=False)  # Класс от 1 до 11
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Уникальный индекс на (subject_id, class_number)
    __table_args__ = (
        Index('idx_subject_class_unique', 'subject_id', 'class_number', unique=True),
    )


# Установка relationship после определения SubjectClass
Subject.classes = relationship('SubjectClass', backref='subject', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='SubjectClass.subject_id')


class StudentResult(Base):
    """Student test results."""
    __tablename__ = 'student_results'
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(String(100), nullable=False, index=True)
    student_name = Column(String(200), nullable=False)
    student_class = Column(String(50), nullable=False)
    answers = Column(JSON, nullable=False)  # Student answers
    results = Column(JSON, nullable=False)  # Detailed results per field
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    percentage = Column(Float, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible


class AICheckLog(Base):
    """Log of AI answer checks."""
    __tablename__ = 'ai_check_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    student_result_id = Column(Integer, nullable=True)  # Foreign key to student_results
    field_id = Column(String(100), nullable=False)
    student_answer = Column(Text, nullable=False)
    correct_variants = Column(JSON, nullable=False)
    question_context = Column(Text, nullable=True)
    ai_provider = Column(String(50), nullable=False)
    ai_model = Column(String(100), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    explanation = Column(Text, nullable=True)
    from_cache = Column(Boolean, default=False)
    check_method = Column(String(50), nullable=True)  # exact, fuzzy, semantic, ai
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class SystemMetric(Base):
    """System metrics for monitoring."""
    __tablename__ = 'system_metrics'
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50), nullable=True)
    tags = Column(JSON, nullable=True)  # Additional metadata
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


class AIModel(Base):
    """AI Model configuration."""
    __tablename__ = 'ai_models'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # Отображаемое имя модели
    provider = Column(String(50), nullable=False, index=True)  # 'ollama', 'gemini', 'groq', 'cohere'
    model_name = Column(String(200), nullable=False)  # Техническое имя модели
    requires_api_key = Column(Boolean, default=False, nullable=False)  # Требует ли API ключ
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # Доступна ли модель
    description = Column(Text, nullable=True)  # Описание модели
    config_json = Column(JSON, nullable=True)  # Дополнительные настройки (temperature, max_tokens и т.д.)
    priority = Column(Integer, default=0, nullable=False)  # Приоритет отображения (меньше = выше)
    max_requests_per_minute = Column(Integer, nullable=True)  # Лимит запросов в минуту
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Audit log for tracking admin actions."""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # ID пользователя, выполнившего действие
    username = Column(String(100), nullable=True)  # Логин для удобства
    action = Column(String(50), nullable=False, index=True)  # create_teacher, update_teacher, delete_teacher, create_test, etc.
    target_type = Column(String(50), nullable=True)  # teacher, test
    target_id = Column(Integer, nullable=True)  # ID объекта
    details = Column(JSON, nullable=True)  # Детали действия
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# Database helper functions
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


def drop_db():
    """Drop all database tables (use with caution!)."""
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All database tables dropped!")


if __name__ == "__main__":
    # Create tables when run directly
    init_db()
