"""widen bin columns

Revision ID: 002
Revises: 001
Create Date: 2026-10-13

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('invoices', 'supplier_bin', type_=sa.String(20))
    op.alter_column('invoices', 'buyer_bin', type_=sa.String(20))
    op.alter_column('cases', 'bin', type_=sa.String(20))
    op.alter_column('organizations', 'bin', type_=sa.String(20))
    op.alter_column('persons', 'iin', type_=sa.String(20))


def downgrade():
    op.alter_column('invoices', 'supplier_bin', type_=sa.String(12))
    op.alter_column('invoices', 'buyer_bin', type_=sa.String(12))
    op.alter_column('cases', 'bin', type_=sa.String(12))
    op.alter_column('organizations', 'bin', type_=sa.String(12))
    op.alter_column('persons', 'iin', type_=sa.String(12))
