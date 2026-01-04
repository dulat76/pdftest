"""add ai_models table and user fields

Revision ID: add_ai_models_table
Revises: add_ai_checking_enabled
Create Date: 2026-01-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
import json


# revision identifiers, used by Alembic.
revision = 'add_ai_models_table'
down_revision = 'add_ai_checking_enabled'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # 1. Создание таблицы ai_models
    if 'ai_models' not in inspector.get_table_names():
        op.create_table(
            'ai_models',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('provider', sa.String(length=50), nullable=False),
            sa.Column('model_name', sa.String(length=200), nullable=False),
            sa.Column('requires_api_key', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('config_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('max_requests_per_minute', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_ai_models_id', 'ai_models', ['id'], unique=False)
        op.create_index('ix_ai_models_provider', 'ai_models', ['provider'], unique=False)
        op.create_index('ix_ai_models_is_active', 'ai_models', ['is_active'], unique=False)
    
    # 2. Добавление полей в таблицу users
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'ai_model_id' not in columns:
        op.add_column('users', sa.Column('ai_model_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_users_ai_model_id',
            'users', 'ai_models',
            ['ai_model_id'], ['id'],
            ondelete='SET NULL'
        )
        op.create_index('ix_users_ai_model_id', 'users', ['ai_model_id'], unique=False)
    
    if 'ai_api_key' not in columns:
        op.add_column('users', sa.Column('ai_api_key', sa.String(length=500), nullable=True))
    
    # 3. Создание начальных записей моделей
    # Проверяем, что таблица создана и вставляем данные
    if 'ai_models' in inspector.get_table_names():
        # Проверяем, есть ли уже записи
        result = connection.execute(sa.text("SELECT COUNT(*) FROM ai_models")).scalar()
        if result == 0:
            op.execute("""
                INSERT INTO ai_models (name, provider, model_name, requires_api_key, is_active, description, priority, config_json, created_at, updated_at)
                VALUES 
                (
                    'Встроенная модель qwen2.5:1.5b',
                    'ollama',
                    'qwen2.5:1.5b',
                    false,
                    true,
                    'Локальная модель Ollama, не требует API ключа. Быстрая и эффективная для проверки ответов.',
                    1,
                    '{"temperature": 0.1, "max_tokens": 200, "top_p": 0.8, "top_k": 10}'::jsonb,
                    NOW(),
                    NOW()
                ),
                (
                    'Gemini 2.0 Flash',
                    'gemini',
                    'gemini-2.0-flash',
                    true,
                    true,
                    'Модель Google Gemini, требует API ключ. Высокое качество проверки ответов.',
                    2,
                    '{"temperature": 0.1, "max_tokens": 200, "top_p": 0.8}'::jsonb,
                    NOW(),
                    NOW()
                );
            """)


def downgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Удаление полей из users
    if 'ai_api_key' in columns:
        op.drop_column('users', 'ai_api_key')
    
    if 'ai_model_id' in columns:
        op.drop_constraint('fk_users_ai_model_id', 'users', type_='foreignkey')
        op.drop_index('ix_users_ai_model_id', table_name='users')
        op.drop_column('users', 'ai_model_id')
    
    # Удаление таблицы ai_models
    if 'ai_models' in inspector.get_table_names():
        op.drop_index('ix_ai_models_is_active', table_name='ai_models')
        op.drop_index('ix_ai_models_provider', table_name='ai_models')
        op.drop_index('ix_ai_models_id', table_name='ai_models')
        op.drop_table('ai_models')

