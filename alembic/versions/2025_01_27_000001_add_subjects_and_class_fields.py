"""add_subjects_and_class_fields

Revision ID: add_subjects_class
Revises: add_user_teacher_fields
Create Date: 2025-01-27 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_subjects_class'
down_revision = 'add_user_teacher_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Создание таблицы subjects
    op.create_table('subjects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('name_slug', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subjects_name_slug'), 'subjects', ['name_slug'], unique=True)
    op.create_index(op.f('ix_subjects_is_active'), 'subjects', ['is_active'], unique=False)
    op.create_unique_constraint('uq_subjects_name', 'subjects', ['name'])
    
    # Добавление полей в таблицу templates
    op.add_column('templates', sa.Column('class_number', sa.Integer(), nullable=True))
    op.add_column('templates', sa.Column('subject_id', sa.Integer(), nullable=True))
    
    # Создание индекса на subject_id
    op.create_index(op.f('ix_templates_subject_id'), 'templates', ['subject_id'], unique=False)
    
    # Удаление старого индекса и создание нового
    op.drop_index('idx_username_topic_slug', table_name='templates')
    op.create_index('idx_username_subject_topic', 'templates', ['created_by_username', 'subject_id', 'topic_slug'], unique=True)


def downgrade():
    # Удаление индексов и полей из templates
    op.drop_index('idx_username_subject_topic', table_name='templates')
    op.create_index('idx_username_topic_slug', 'templates', ['created_by_username', 'topic_slug'], unique=True)
    op.drop_index(op.f('ix_templates_subject_id'), table_name='templates')
    op.drop_column('templates', 'subject_id')
    op.drop_column('templates', 'class_number')
    
    # Удаление таблицы subjects
    op.drop_index(op.f('ix_subjects_is_active'), table_name='subjects')
    op.drop_index(op.f('ix_subjects_name_slug'), table_name='subjects')
    op.drop_table('subjects')


