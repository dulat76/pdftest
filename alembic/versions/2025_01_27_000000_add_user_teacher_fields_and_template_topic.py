"""add_user_teacher_fields_and_template_topic

Revision ID: add_user_teacher_fields
Revises: 
Create Date: 2025-01-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_user_teacher_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Добавление полей в таблицу users
    op.add_column('users', sa.Column('role', sa.String(length=20), nullable=False, server_default='teacher'))
    op.add_column('users', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('city_code', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('school', sa.String(length=200), nullable=True))
    op.add_column('users', sa.Column('school_code', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('expiration_date', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('max_tests_limit', sa.Integer(), nullable=True))
    
    # Создание индекса на role
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    
    # Добавление полей в таблицу templates
    op.add_column('templates', sa.Column('topic', sa.String(length=200), nullable=True))
    op.add_column('templates', sa.Column('created_by_username', sa.String(length=100), nullable=True))
    op.add_column('templates', sa.Column('topic_slug', sa.String(length=200), nullable=True))
    op.add_column('templates', sa.Column('is_public', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('templates', sa.Column('access_count', sa.Integer(), nullable=True, server_default='0'))
    
    # Создание индексов для templates
    op.create_index(op.f('ix_templates_created_by_username'), 'templates', ['created_by_username'], unique=False)
    op.create_index(op.f('ix_templates_is_active'), 'templates', ['is_active'], unique=False)
    
    # Создание уникального индекса на (created_by_username, topic_slug)
    op.create_index('idx_username_topic_slug', 'templates', ['created_by_username', 'topic_slug'], unique=True)
    
    # Создание таблицы audit_logs
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=True),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)


def downgrade():
    # Удаление таблицы audit_logs
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    
    # Удаление индексов и полей из templates
    op.drop_index('idx_username_topic_slug', table_name='templates')
    op.drop_index(op.f('ix_templates_is_active'), table_name='templates')
    op.drop_index(op.f('ix_templates_created_by_username'), table_name='templates')
    op.drop_column('templates', 'access_count')
    op.drop_column('templates', 'is_public')
    op.drop_column('templates', 'topic_slug')
    op.drop_column('templates', 'created_by_username')
    op.drop_column('templates', 'topic')
    
    # Удаление индексов и полей из users
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_column('users', 'max_tests_limit')
    op.drop_column('users', 'expiration_date')
    op.drop_column('users', 'school_code')
    op.drop_column('users', 'school')
    op.drop_column('users', 'city_code')
    op.drop_column('users', 'city')
    op.drop_column('users', 'role')




