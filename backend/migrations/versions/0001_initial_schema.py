"""Create user, connected form and candidate tables."""

from alembic import op

from app import models

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    models.User.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    models.User.metadata.drop_all(bind=op.get_bind())
