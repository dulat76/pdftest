"""Database models using SQLAlchemy."""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://flask_user:flask_password123@185.22.64.9:5432/flask_db')
DB_SCHEMA = os.getenv('DB_SCHEMA', 'public')

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    echo=False,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    connect_args={
        "options": f"-c search_path={DB_SCHEMA},public" if DB_SCHEMA != 'public' else {}
    }
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


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
