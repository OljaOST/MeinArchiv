"""Dokumenttabelle als Ausgangspunkt."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dokumente",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dateiname", sa.String(length=255), nullable=False),
        sa.Column("inhalt", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("dokumente")