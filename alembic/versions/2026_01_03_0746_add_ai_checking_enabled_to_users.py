"""add ai_checking_enabled to users

Revision ID: add_ai_checking_enabled
Revises: 
Create Date: 2026-01-03 07:46:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_ai_checking_enabled'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем поле ai_checking_enabled в таблицу users
    op.add_column('users', sa.Column('ai_checking_enabled', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    # Удаляем поле ai_checking_enabled из таблицы users
    op.drop_column('users', 'ai_checking_enabled')

