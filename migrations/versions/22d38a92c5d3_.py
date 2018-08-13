"""empty message

Revision ID: 22d38a92c5d3
Revises: 8cc84b8cf0a0
Create Date: 2018-08-12 11:47:55.150374

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '22d38a92c5d3'
down_revision = '8cc84b8cf0a0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('pub_id', 'pubmed_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('pub_id', sa.Column('pubmed_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
