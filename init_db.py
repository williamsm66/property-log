from app import app, db, Property

def init_database():
    with app.app_context():
        # Drop all existing tables
        db.drop_all()
        print("Dropped all existing tables")
        
        # Create all tables
        db.create_all()
        print("Created all tables")
        
        # Verify the table exists and show its structure
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print("\nCreated tables:", tables)
        
        if 'property' in tables:
            columns = inspector.get_columns('property')
            print("\nColumns in 'property' table:")
            for column in columns:
                print(f"- {column['name']} ({column['type']})")

if __name__ == "__main__":
    init_database()
