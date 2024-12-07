from app import db
from datetime import datetime

def upgrade():
    # Add viewing date columns
    with db.engine.connect() as conn:
        conn.execute('''
            ALTER TABLE property 
            ADD COLUMN viewing_date_1 DATETIME,
            ADD COLUMN viewing_date_2 DATETIME,
            ADD COLUMN viewing_date_3 DATETIME,
            ADD COLUMN viewing_date_4 DATETIME;
        ''')

def downgrade():
    # Remove viewing date columns
    with db.engine.connect() as conn:
        conn.execute('''
            ALTER TABLE property 
            DROP COLUMN viewing_date_1,
            DROP COLUMN viewing_date_2,
            DROP COLUMN viewing_date_3,
            DROP COLUMN viewing_date_4;
        ''')

if __name__ == '__main__':
    upgrade()
