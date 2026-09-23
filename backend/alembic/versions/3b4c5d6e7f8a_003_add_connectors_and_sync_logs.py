"""003_add_connectors_and_sync_logs

Revision ID: 3b4c5d6e7f8a
Revises: 2a3b4c5d6e7f
Create Date: 2026-09-22 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.database import GUID, JSONType


# revision identifiers, used by Alembic.
revision: str = '3b4c5d6e7f8a'
down_revision: Union[str, Sequence[str], None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create platform_connectors table
    try:
        op.create_table(
            'platform_connectors',
            sa.Column('id', GUID(), primary_key=True),
            sa.Column('platform_id', GUID(), sa.ForeignKey('platforms.id', ondelete='CASCADE'), nullable=False),
            sa.Column('connector_type', sa.String(length=50), nullable=False),
            sa.Column('connector_key', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=50), server_default='COMING_SOON', nullable=False),
            sa.Column('capabilities', JSONType(), nullable=False),
            sa.Column('is_enabled', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_platform_connectors_platform_id', 'platform_connectors', ['platform_id'])
        op.create_index('ix_platform_connectors_connector_key', 'platform_connectors', ['connector_key'])
    except Exception:
        pass

    # 2. Create sync_logs table
    try:
        op.create_table(
            'sync_logs',
            sa.Column('id', GUID(), primary_key=True),
            sa.Column('connection_id', GUID(), sa.ForeignKey('connections.id', ondelete='CASCADE'), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=False),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=50), server_default='STARTED', nullable=False),
            sa.Column('records_processed', sa.Integer(), server_default='0', nullable=False),
            sa.Column('records_created', sa.Integer(), server_default='0', nullable=False),
            sa.Column('records_updated', sa.Integer(), server_default='0', nullable=False),
            sa.Column('error_code', sa.String(length=100), nullable=True),
            sa.Column('safe_error_message', sa.String(length=500), nullable=True),
        )
        op.create_index('ix_sync_logs_connection_id', 'sync_logs', ['connection_id'])
    except Exception:
        pass

    # 3. Add columns to connections table
    try:
        op.add_column('connections', sa.Column('connector_key', sa.String(length=100), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('connections', sa.Column('last_sync_status', sa.String(length=50), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('connections', sa.Column('last_sync_error', sa.String(length=500), nullable=True))
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_column('connections', 'last_sync_error')
        op.drop_column('connections', 'last_sync_status')
        op.drop_column('connections', 'connector_key')
    except Exception:
        pass

    try:
        op.drop_index('ix_sync_logs_connection_id', table_name='sync_logs')
        op.drop_table('sync_logs')
    except Exception:
        pass

    try:
        op.drop_index('ix_platform_connectors_connector_key', table_name='platform_connectors')
        op.drop_index('ix_platform_connectors_platform_id', table_name='platform_connectors')
        op.drop_table('platform_connectors')
    except Exception:
        pass
