"""add_user_name_fields_and_subject_classes

Revision ID: add_user_names_subject_classes
Revises: add_subjects_class
Create Date: 2026-01-01 17:04:24.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_user_names_subject_classes'
down_revision = 'add_subjects_class'
branch_labels = None
depends_on = None


def upgrade():
    # Добавление полей first_name и last_name в таблицу users
    op.add_column('users', sa.Column('first_name', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(length=100), nullable=True))
    
    # Для существующих записей установим значения по умолчанию
    # ВАЖНО: После миграции нужно будет заполнить эти поля вручную для существующих записей
    op.execute("UPDATE users SET first_name = 'Не указано' WHERE first_name IS NULL")
    op.execute("UPDATE users SET last_name = 'Не указано' WHERE last_name IS NULL")
    
    # Теперь делаем поля обязательными
    op.alter_column('users', 'first_name', nullable=False)
    op.alter_column('users', 'last_name', nullable=False)
    
    # Изменение email на NOT NULL
    # Сначала проверим, есть ли NULL значения
    # Если есть, нужно будет заполнить их вручную перед миграцией
    # Для новых записей email будет обязательным
    # ВАЖНО: Если в БД есть записи с NULL email, нужно их заполнить перед выполнением этой миграции
    op.execute("UPDATE users SET email = username || '@example.com' WHERE email IS NULL")
    op.alter_column('users', 'email', nullable=False)
    
    # Создание таблицы subject_classes
    op.create_table('subject_classes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('class_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subject_classes_subject_id'), 'subject_classes', ['subject_id'], unique=False)
    op.create_index('idx_subject_class_unique', 'subject_classes', ['subject_id', 'class_number'], unique=True)


def downgrade():
    # Удаление таблицы subject_classes
    op.drop_index('idx_subject_class_unique', table_name='subject_classes')
    op.drop_index(op.f('ix_subject_classes_subject_id'), table_name='subject_classes')
    op.drop_table('subject_classes')
    
    # Откат изменений email (делаем nullable=True)
    op.alter_column('users', 'email', nullable=True)
    
    # Удаление полей first_name и last_name
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')

