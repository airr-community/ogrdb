"""empty message

Revision ID: 248699827598
Revises: 8a6805bd4b2c
Create Date: 2018-08-06 11:23:01.188237

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '248699827598'
down_revision = '8a6805bd4b2c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('repertoire_ibfk_1', 'repertoire', type_='foreignkey')
    op.create_foreign_key(None, 'repertoire', 'submission', ['submission_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'repertoire', type_='foreignkey')
    op.create_foreign_key('repertoire_ibfk_1', 'repertoire', 'repertoire', ['submission_id'], ['id'])
    # ### end Alembic commands ###
