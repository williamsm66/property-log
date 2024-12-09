"""add document sessions table

Revision ID: add_document_sessions
Revises: 
Create Date: 2024-12-09 13:54:41.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_document_sessions'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('document_sessions',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('documents', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('initial_analysis', sa.Text(), nullable=True),
        sa.Column('qa_history', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['property_id'], ['property.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('document_sessions')
