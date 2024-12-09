"""add legal pack documents column

Revision ID: add_legal_pack_documents
Revises: 
Create Date: 2024-12-09 13:58:21.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_legal_pack_documents'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('property', sa.Column('legal_pack_documents', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('property', 'legal_pack_documents')
