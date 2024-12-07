from flask import current_app
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, DateTime, Float, String, Text

def upgrade():
    # Add new columns to the property table
    current_app.extensions['migrate'].db.engine.execute('''
        ALTER TABLE property 
        ADD COLUMN legal_pack_url VARCHAR(500),
        ADD COLUMN legal_pack_available BOOLEAN DEFAULT FALSE,
        ADD COLUMN risk_level VARCHAR(20),
        ADD COLUMN key_risks TEXT,
        ADD COLUMN extra_fees FLOAT DEFAULT 0,
        ADD COLUMN auction_date DATETIME
    ''')

def downgrade():
    # Remove the new columns if needed
    current_app.extensions['migrate'].db.engine.execute('''
        ALTER TABLE property 
        DROP COLUMN legal_pack_url,
        DROP COLUMN legal_pack_available,
        DROP COLUMN risk_level,
        DROP COLUMN key_risks,
        DROP COLUMN extra_fees,
        DROP COLUMN auction_date
    ''')
