"""empty message

Revision ID: 53cc366f34d0
Revises: f5d1a02db088
Create Date: 2018-08-01 17:04:05.365244

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '53cc366f34d0'
down_revision = 'f5d1a02db088'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('submission', sa.Column('owner_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'submission', 'user', ['owner_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'submission', type_='foreignkey')
    op.drop_column('submission', 'owner_id')
    # ### end Alembic commands ###
