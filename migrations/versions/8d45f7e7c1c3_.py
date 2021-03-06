"""empty message

Revision ID: 8d45f7e7c1c3
Revises: d1031ecb8b48
Create Date: 2018-08-13 16:29:05.971224

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8d45f7e7c1c3'
down_revision = 'd1031ecb8b48'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('acknowledgements', 'ack_name')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('acknowledgements', sa.Column('ack_name', mysql.VARCHAR(length=10000), nullable=True))
    # ### end Alembic commands ###
