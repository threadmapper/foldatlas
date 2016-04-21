"""empty message

Revision ID: 6fe4187803d7
Revises: 1740de11ccfe
Create Date: 2016-04-20 17:42:53.188571

"""
# revision identifiers, used by Alembic.
revision = '6fe4187803d7'
down_revision = '1740de11ccfe'

from alembic import op
import sqlalchemy as sa
from database import db_session

def upgrade():
    # we need drop if exists so that script fails don't break the import
    db_session.execute("DROP TABLE IF EXISTS raw_replicate_counts")
    op.create_table('raw_replicate_counts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nucleotide_measurement_run_id', sa.Integer(), nullable=True),
        sa.Column('transcript_id', sa.String(length=256), nullable=True),
        sa.Column('minusplus_id', sa.String(length=256), nullable=False),
        sa.Column('bio_replicate_id', sa.Integer(), nullable=False),
        sa.Column('tech_replicate_id', sa.Integer(), nullable=False),
        sa.Column('values', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['nucleotide_measurement_run_id'], ['nucleotide_measurement_run.id'], ),
        sa.ForeignKeyConstraint(['transcript_id'], ['transcript.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    from importers import import_raw_replicate_counts
    import_raw_replicate_counts()


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('raw_replicate_counts')
    ### end Alembic commands ###
