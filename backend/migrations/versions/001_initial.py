"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-01-01

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('roles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.String(255)),
        sa.Column('permissions', sa.JSON()),
    )
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('last_login', sa.DateTime()),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table('cases',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(36), unique=True),
        sa.Column('number', sa.String(50), unique=True, nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('organization_name', sa.String(500)),
        sa.Column('bin', sa.String(12)),
        sa.Column('basis', sa.Text()),
        sa.Column('basis_date', sa.Date()),
        sa.Column('requesting_body', sa.String(500)),
        sa.Column('subject', sa.Text()),
        sa.Column('period_start', sa.Date()),
        sa.Column('period_end', sa.Date()),
        sa.Column('responsible_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('status', sa.String(50), default='open'),
        sa.Column('comment', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id')),
    )
    op.create_index('ix_cases_number', 'cases', ['number'])
    op.create_index('ix_cases_bin', 'cases', ['bin'])
    op.create_index('ix_cases_status', 'cases', ['status'])

    op.create_table('case_members',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role_in_case', sa.String(50), default='analyst'),
        sa.Column('added_at', sa.DateTime()),
        sa.UniqueConstraint('case_id', 'user_id', name='uq_case_user'),
    )

    op.create_table('organizations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('bin', sa.String(12), unique=True),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('short_name', sa.String(255)),
        sa.Column('address', sa.Text()),
        sa.Column('status', sa.String(50)),
        sa.Column('source', sa.String(255)),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    op.create_table('persons',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('iin', sa.String(12), unique=True),
        sa.Column('full_name', sa.String(500), nullable=False),
        sa.Column('birth_date', sa.Date()),
        sa.Column('source', sa.String(255)),
        sa.Column('created_at', sa.DateTime()),
    )

    op.create_table('source_files',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(36), unique=True),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('original_filename', sa.String(500), nullable=False),
        sa.Column('stored_filename', sa.String(500), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('file_size', sa.BigInteger()),
        sa.Column('mime_type', sa.String(100)),
        sa.Column('file_hash', sa.String(64)),
        sa.Column('data_type', sa.String(50), default='esf'),
        sa.Column('source_description', sa.String(500)),
        sa.Column('uploaded_by_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('uploaded_at', sa.DateTime()),
        sa.Column('status', sa.String(50), default='uploaded'),
    )

    op.create_table('import_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_file_id', sa.Integer(), sa.ForeignKey('source_files.id'), nullable=False),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('finished_at', sa.DateTime()),
        sa.Column('total_rows', sa.Integer(), default=0),
        sa.Column('success_rows', sa.Integer(), default=0),
        sa.Column('error_rows', sa.Integer(), default=0),
        sa.Column('duplicate_rows', sa.Integer(), default=0),
        sa.Column('column_mapping', sa.JSON()),
        sa.Column('error_report', sa.JSON()),
        sa.Column('result_summary', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
    )

    op.create_table('invoices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('source_file_id', sa.Integer(), sa.ForeignKey('source_files.id')),
        sa.Column('import_job_id', sa.Integer(), sa.ForeignKey('import_jobs.id')),
        sa.Column('document_number', sa.String(100)),
        sa.Column('document_date', sa.Date()),
        sa.Column('operation_type', sa.String(20)),
        sa.Column('supplier_name', sa.String(500)),
        sa.Column('supplier_bin', sa.String(12)),
        sa.Column('buyer_name', sa.String(500)),
        sa.Column('buyer_bin', sa.String(12)),
        sa.Column('total_amount', sa.Numeric(18, 2)),
        sa.Column('currency', sa.String(10), default='KZT'),
        sa.Column('original_row', sa.Integer()),
        sa.Column('raw_data', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
    )

    op.create_table('invoice_lines',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id'), nullable=False),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('product_name', sa.String(1000), nullable=False),
        sa.Column('product_name_normalized', sa.String(1000)),
        sa.Column('product_code', sa.String(100)),
        sa.Column('quantity', sa.Numeric(18, 4)),
        sa.Column('unit', sa.String(50)),
        sa.Column('unit_price', sa.Numeric(18, 4)),
        sa.Column('amount', sa.Numeric(18, 2)),
        sa.Column('vat_amount', sa.Numeric(18, 2)),
        sa.Column('original_row', sa.Integer()),
        sa.Column('source_file_id', sa.Integer(), sa.ForeignKey('source_files.id')),
        sa.Column('created_at', sa.DateTime()),
    )

    op.create_table('product_matches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('purchase_line_id', sa.Integer(), sa.ForeignKey('invoice_lines.id'), nullable=False),
        sa.Column('sale_line_id', sa.Integer(), sa.ForeignKey('invoice_lines.id'), nullable=False),
        sa.Column('match_type', sa.String(20)),
        sa.Column('similarity_score', sa.Float()),
        sa.Column('price_diff', sa.Numeric(18, 4)),
        sa.Column('price_diff_percent', sa.Float()),
        sa.Column('quantity_diff', sa.Numeric(18, 4)),
        sa.Column('status', sa.String(30), default='proposed'),
        sa.Column('reviewed_by_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('reviewed_at', sa.DateTime()),
        sa.Column('comment', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
    )

    op.create_table('analytical_flags',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('flag_number', sa.String(20)),
        sa.Column('category', sa.String(100)),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('severity', sa.String(20), default='medium'),
        sa.Column('deviation_value', sa.Float()),
        sa.Column('rule_applied', sa.String(255)),
        sa.Column('source_entities', sa.JSON()),
        sa.Column('status', sa.String(30), default='new'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    op.create_table('flag_reviews',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('flag_id', sa.Integer(), sa.ForeignKey('analytical_flags.id'), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action', sa.String(50)),
        sa.Column('comment', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
    )

    op.create_table('report_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(36), unique=True),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('title', sa.String(500)),
        sa.Column('status', sa.String(30), default='draft'),
        sa.Column('content_json', sa.JSON()),
        sa.Column('file_path', sa.String(1000)),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.Column('comment', sa.Text()),
    )

    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id')),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50)),
        sa.Column('entity_id', sa.Integer()),
        sa.Column('details', sa.JSON()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('created_at', sa.DateTime()),
    )

    op.create_table('counterparties',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('bin_or_iin', sa.String(12)),
        sa.Column('role', sa.String(50)),
        sa.Column('documents_count', sa.Integer(), default=0),
        sa.Column('purchase_amount', sa.Numeric(18, 2), default=0),
        sa.Column('sale_amount', sa.Numeric(18, 2), default=0),
        sa.Column('share_percent', sa.Float()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    op.create_table('entity_relations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('relation_type', sa.String(100), nullable=False),
        sa.Column('from_entity_type', sa.String(50)),
        sa.Column('from_entity_id', sa.Integer()),
        sa.Column('from_entity_label', sa.String(500)),
        sa.Column('to_entity_type', sa.String(50)),
        sa.Column('to_entity_id', sa.Integer()),
        sa.Column('to_entity_label', sa.String(500)),
        sa.Column('source', sa.String(255)),
        sa.Column('source_date', sa.Date()),
        sa.Column('valid_from', sa.Date()),
        sa.Column('valid_to', sa.Date()),
        sa.Column('status', sa.String(30), default='unverified'),
        sa.Column('comment', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
    )

    op.create_table('procurement_contracts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False),
        sa.Column('procurement_number', sa.String(100)),
        sa.Column('contract_number', sa.String(100)),
        sa.Column('contract_date', sa.Date()),
        sa.Column('customer_name', sa.String(500)),
        sa.Column('customer_bin', sa.String(12)),
        sa.Column('supplier_name', sa.String(500)),
        sa.Column('supplier_bin', sa.String(12)),
        sa.Column('subject', sa.Text()),
        sa.Column('amount', sa.Numeric(18, 2)),
        sa.Column('status', sa.String(50)),
        sa.Column('execution_period', sa.String(255)),
        sa.Column('source_url', sa.String(1000)),
        sa.Column('source_file_id', sa.Integer(), sa.ForeignKey('source_files.id')),
        sa.Column('data_obtained_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
    )


def downgrade():
    for t in ['procurement_contracts','entity_relations','counterparties','audit_logs',
              'report_versions','flag_reviews','analytical_flags','product_matches',
              'invoice_lines','invoices','import_jobs','source_files','persons',
              'organizations','case_members','cases','users','roles']:
        op.drop_table(t)
