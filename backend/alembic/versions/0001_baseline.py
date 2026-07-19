"""Baseline revision.

The schema up to this point is created by ``Base.metadata.create_all`` at app
startup (see ``app/database.py::init_db``), which only ADDS missing tables and
never alters existing ones. This empty revision marks that baseline so future
schema CHANGES (new columns, type changes, constraints) can ship as real
Alembic migrations:

    cd backend
    alembic revision --autogenerate -m "describe change"
    alembic upgrade head

To adopt migrations on an existing database, stamp it first:

    alembic stamp 0001

Revision ID: 0001
Revises:
Create Date: 2026-07-19
"""

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline — schema already exists via create_all; nothing to do.
    pass


def downgrade() -> None:
    pass
