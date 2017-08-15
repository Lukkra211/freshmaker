"""empty message

Revision ID: 43b3c6580af7
Revises: 8d2e9cd99c54
Create Date: 2017-08-15 10:29:33.224878

"""

# revision identifiers, used by Alembic.
revision = '43b3c6580af7'
down_revision = '8d2e9cd99c54'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('events', sa.Column('released', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('events', 'released')
    # ### end Alembic commands ###
