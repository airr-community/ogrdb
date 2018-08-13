"""empty message

Revision ID: dd15faa44bec
Revises: 75e2c5bb9072
Create Date: 2018-08-10 09:35:07.571298

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'dd15faa44bec'
down_revision = '75e2c5bb9072'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('repertoire', 'miarr_compliant')
    op.drop_column('repertoire', 'primers_not_overlapping')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('repertoire', sa.Column('primers_not_overlapping', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True))
    op.add_column('repertoire', sa.Column('miarr_compliant', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
