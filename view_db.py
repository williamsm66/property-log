from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import json
from datetime import datetime

app = Flask(__name__)

# Configure database
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///property_log.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define Property model
class Property(db.Model):
    __tablename__ = 'property'
    
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(500), nullable=True)
    purchase_price = db.Column(db.Float)
    legal_pack_analysis = db.Column(db.Text, nullable=True)
    legal_pack_qa_history = db.Column(db.Text, nullable=True)
    legal_pack_documents = db.Column(db.Text, nullable=True)

def view_properties():
    with app.app_context():
        properties = Property.query.all()
        print(f"\nFound {len(properties)} properties in database:")
        
        for prop in properties:
            print("\n" + "="*80)
            print(f"Property ID: {prop.id}")
            print(f"Address: {prop.address}")
            print(f"Purchase Price: £{prop.purchase_price:,.2f}" if prop.purchase_price else "Purchase Price: Not set")
            print(f"Legal Pack Analysis Available: {'Yes' if prop.legal_pack_analysis else 'No'}")
            print(f"Legal Pack Documents Available: {'Yes' if prop.legal_pack_documents else 'No'}")
            
            if prop.legal_pack_qa_history:
                qa_history = json.loads(prop.legal_pack_qa_history)
                print(f"\nQ&A History ({len(qa_history)} questions):")
                for i, qa in enumerate(qa_history, 1):
                    print(f"\nQ{i}: {qa['question']}")
                    print(f"A{i}: {qa['answer'][:200]}..." if len(qa['answer']) > 200 else f"A{i}: {qa['answer']}")

            if prop.legal_pack_documents:
                docs = json.loads(prop.legal_pack_documents)
                print(f"\nStored Documents ({len(docs)}):")
                for doc in docs:
                    print(f"- {doc['name']} ({len(doc['content'])} chars)")

if __name__ == "__main__":
    view_properties()
