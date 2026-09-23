"""005_add_account_aggregator_consent_fields

Revision ID: 5d6e7f8a9b0c
Revises: 4c5d6e7f8a9b
Create Date: 2026-09-23 02:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.database import GUID, JSONType


# revision identifiers, used by Alembic.
revision: str = '5d6e7f8a9b0c'
down_revision: Union[str, Sequence[str], None] = '4c5d6e7f8a9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    try:
        op.add_column('connections', sa.Column('provider', sa.String(length=50), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('connections', sa.Column('consent_id', sa.String(length=100), nullable=True))
        op.create_index('ix_connections_consent_id', 'connections', ['consent_id'])
    except Exception:
        pass

    try:
        op.add_column('connections', sa.Column('consent_status', sa.String(length=50), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('connections', sa.Column('consent_created_at', sa.DateTime(), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('connections', sa.Column('consent_expires_at', sa.DateTime(), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('connections', sa.Column('last_consent_sync', sa.DateTime(), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('connections', sa.Column('last_data_fetch', sa.DateTime(), nullable=True))
    except Exception:
        pass

    try:
        op.add_column('connections', sa.Column('provider_metadata', JSONType(), server_default='{}', nullable=False))
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_column('connections', 'provider_metadata')
    except Exception:
        pass

    try:
        op.drop_column('connections', 'last_data_fetch')
    except Exception:
        pass

    try:
        op.drop_column('connections', 'last_consent_sync')
    except Exception:
        pass

    try:
        op.drop_column('connections', 'consent_expires_at')
    except Exception:
        pass

    try:
        op.drop_column('connections', 'consent_created_at')
    except Exception:
        pass

    try:
        op.drop_column('connections', 'consent_status')
    except Exception:
        pass

    try:
        op.drop_index('ix_connections_consent_id', table_name='connections')
        op.drop_column('connections', 'consent_id')
    except Exception:
        pass

    try:
        op.drop_column('connections', 'provider')
    except Exception:
        pass
