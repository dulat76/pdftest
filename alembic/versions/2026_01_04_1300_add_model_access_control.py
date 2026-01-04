"""add model access control fields

Revision ID: add_model_access_control
Revises: abf3ac8cb319
Create Date: 2026-01-04 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_model_access_control'
down_revision = 'abf3ac8cb319'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # 1. Добавление поля is_available_for_teachers в таблицу ai_models
    if 'ai_models' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('ai_models')]
        if 'is_available_for_teachers' not in columns:
            op.add_column('ai_models', sa.Column('is_available_for_teachers', sa.Boolean(), nullable=False, server_default='false'))
    
    # 2. Добавление поля ollama_access_enabled в таблицу users
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'ollama_access_enabled' not in columns:
        op.add_column('users', sa.Column('ollama_access_enabled', sa.Boolean(), nullable=False, server_default='false'))
    
    # 3. Установить is_available_for_teachers=False для модели Ollama по умолчанию
    if 'ai_models' in inspector.get_table_names():
        op.execute("""
            UPDATE ai_models 
            SET is_available_for_teachers = false 
            WHERE provider = 'ollama';
        """)


def downgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Удаление полей
    if 'ollama_access_enabled' in columns:
        op.drop_column('users', 'ollama_access_enabled')
    
    if 'ai_models' in inspector.get_table_names():
        ai_models_columns = [col['name'] for col in inspector.get_columns('ai_models')]
        if 'is_available_for_teachers' in ai_models_columns:
            op.drop_column('ai_models', 'is_available_for_teachers')

