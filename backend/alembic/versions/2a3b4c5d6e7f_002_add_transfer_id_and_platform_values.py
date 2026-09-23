"""002_add_transfer_id_and_platform_values

Revision ID: 2a3b4c5d6e7f
Revises: 166a9c189bce
Create Date: 2026-09-21 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, Sequence[str], None] = '166a9c189bce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add transfer_id to transactions table
    try:
        op.add_column('transactions', sa.Column('transfer_id', sa.String(100), nullable=True))
        op.create_index('ix_transactions_transfer_id', 'transactions', ['transfer_id'])
    except Exception:
        pass

    # Add platform_values to portfolio_snapshots table
    try:
        op.add_column('portfolio_snapshots', sa.Column('platform_values', sa.UnicodeText(), server_default='{}', nullable=False))
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index('ix_transactions_transfer_id', table_name='transactions')
        op.drop_column('transactions', 'transfer_id')
    except Exception:
        pass

    try:
        op.drop_column('portfolio_snapshots', 'platform_values')
    except Exception:
        pass
