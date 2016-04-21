"""empty message

Revision ID: 09ddd9e7a518
Revises: c28390c05b73
Create Date: 2016-04-21 15:51:52.015018

"""

# revision identifiers, used by Alembic.
revision = '09ddd9e7a518'
down_revision = 'c28390c05b73'

from alembic import op
from importers import BppmImporter
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('bppm')
    op.create_table('bppm',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transcript_id', sa.String(length=256), nullable=False),
        sa.Column('data', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['transcript_id'], ['transcript.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###

    # now we must populate with data
    BppmImporter().run()
    exit()

def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('bppm')
    ### end Alembic commands ###