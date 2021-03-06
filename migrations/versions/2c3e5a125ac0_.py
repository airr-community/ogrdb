"""empty message

Revision ID: 2c3e5a125ac0
Revises: 4e70e7f082dd
Create Date: 2018-08-23 12:12:11.050441

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2c3e5a125ac0'
down_revision = '4e70e7f082dd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('inferred_sequence_ibfk_1', 'inferred_sequence', type_='foreignkey')
    op.drop_column('inferred_sequence', 'genotype_id')
    op.drop_column('inferred_sequence', 'sequence_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('inferred_sequence', sa.Column('sequence_id', mysql.VARCHAR(length=255), nullable=True))
    op.add_column('inferred_sequence', sa.Column('genotype_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.create_foreign_key('inferred_sequence_ibfk_1', 'inferred_sequence', 'genotype_description', ['genotype_id'], ['id'])
    # ### end Alembic commands ###
