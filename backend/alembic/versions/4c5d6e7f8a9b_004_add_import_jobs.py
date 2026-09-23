"""004_add_import_jobs

Revision ID: 4c5d6e7f8a9b
Revises: 3b4c5d6e7f8a
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.database import GUID, JSONType


# revision identifiers, used by Alembic.
revision: str = '4c5d6e7f8a9b'
down_revision: Union[str, Sequence[str], None] = '3b4c5d6e7f8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    try:
        op.create_table(
            'import_jobs',
            sa.Column('id', GUID(), primary_key=True),
            sa.Column('user_id', GUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('connection_id', GUID(), sa.ForeignKey('connections.id', ondelete='SET NULL'), nullable=True),
            sa.Column('platform_id', GUID(), sa.ForeignKey('platforms.id', ondelete='CASCADE'), nullable=False),
            sa.Column('import_type', sa.String(length=50), nullable=False),
            sa.Column('file_name', sa.String(length=255), nullable=False),
            sa.Column('file_type', sa.String(length=50), nullable=False),
            sa.Column('file_size', sa.Integer(), server_default='0', nullable=False),
            sa.Column('status', sa.String(length=50), server_default='UPLOADED', nullable=False),
            sa.Column('row_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('valid_row_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('warning_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('error_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('new_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('duplicate_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('possible_duplicate_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('error_message', sa.String(length=500), nullable=True),
            sa.Column('column_mapping', JSONType(), nullable=False),
            sa.Column('preview_data', JSONType(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('committed_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_import_jobs_user_id', 'import_jobs', ['user_id'])
        op.create_index('ix_import_jobs_connection_id', 'import_jobs', ['connection_id'])
        op.create_index('ix_import_jobs_platform_id', 'import_jobs', ['platform_id'])
        op.create_index('ix_import_jobs_status', 'import_jobs', ['status'])
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index('ix_import_jobs_status', table_name='import_jobs')
        op.drop_index('ix_import_jobs_platform_id', table_name='import_jobs')
        op.drop_index('ix_import_jobs_connection_id', table_name='import_jobs')
        op.drop_index('ix_import_jobs_user_id', table_name='import_jobs')
        op.drop_table('import_jobs')
    except Exception:
        pass
