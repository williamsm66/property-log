from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from property_scraper import PropertyScraper
import asyncio
import os
import json
import uuid
import shutil
import tempfile
import logging
import anthropic
import zipfile
from werkzeug.utils import secure_filename
import tiktoken
import pytesseract
from pdf2image import convert_from_path
import io
import subprocess
from docx import Document
import PyPDF2
from dotenv import load_dotenv
from werkzeug.serving import WSGIRequestHandler
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This will output to console
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set timeout to 5 minutes
WSGIRequestHandler.protocol_version = "HTTP/1.1"

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Add JSON filter for Jinja2
@app.template_filter('json_loads')
def json_loads_filter(s):
    try:
        return json.loads(s) if s else []
    except:
        return []

# Configure database and uploads
basedir = os.path.abspath(os.path.dirname(__file__))

# Use PostgreSQL in production, SQLite in development
if os.environ.get('DATABASE_URL'):
    # Handle Render.com's DATABASE_URL format
    database_url = os.environ.get('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    db_path = os.path.join(basedir, 'properties.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create a directory for storing documents
STORAGE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / 'document_storage'
try:
    STORAGE_DIR.mkdir(mode=0o777, parents=True, exist_ok=True)
    # Ensure parent directory has right permissions too
    STORAGE_DIR.parent.chmod(0o777)
    STORAGE_DIR.chmod(0o777)
except Exception as e:
    logger.error(f"Error creating storage directory: {str(e)}")

# Set database file permissions if it doesn't exist
if not os.path.exists(db_path):
    open(db_path, 'a').close()  # Create file if it doesn't exist
    os.chmod(db_path, 0o666)  # Set read/write permissions for user and group

# Initialize database
db = SQLAlchemy(app)

def count_tokens(text):
    """Count tokens in text using tiktoken."""
    try:
        # Use cl100k_base encoding which is used by Claude
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}")
        # Return a conservative estimate if tiktoken fails
        return len(text.split()) * 2

class Property(db.Model):
    __tablename__ = 'property'
    
    id = db.Column(db.Integer, primary_key=True)
    rightmove_url = db.Column(db.String(500), nullable=True)
    initial_cash = db.Column(db.Float)
    purchase_price = db.Column(db.Float)
    rooms = db.Column(db.Integer)
    monthly_rent = db.Column(db.Float)
    valuation_after = db.Column(db.Float)
    renovation_cost = db.Column(db.Float)
    bridging_duration = db.Column(db.Integer)
    void_period = db.Column(db.Integer)
    mortgage_ltv = db.Column(db.Float)
    mortgage_rate = db.Column(db.Float)
    lender_fee = db.Column(db.Float)
    bridging_rate = db.Column(db.Float)
    arrangement_rate = db.Column(db.Float)
    broker_rate = db.Column(db.Float)
    management_fee = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    main_photo = db.Column(db.String(500), nullable=True)
    floorplan = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    key_features = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(500), nullable=True)
    is_auction = db.Column(db.Boolean, default=False)
    estate_agent = db.Column(db.String(200), nullable=True)
    nearest_station = db.Column(db.String(200), nullable=True)
    station_distance = db.Column(db.Float, nullable=True)
    bedrooms = db.Column(db.Integer, nullable=True)
    bathrooms = db.Column(db.Integer, nullable=True)
    property_type = db.Column(db.String(100), nullable=True)
    
    # New fields
    legal_pack_url = db.Column(db.String(500), nullable=True)
    legal_pack_available = db.Column(db.Boolean, default=False)
    risk_level = db.Column(db.String(20), nullable=True)
    key_risks = db.Column(db.Text, nullable=True)
    extra_fees = db.Column(db.Float, default=0)
    auction_date = db.Column(db.Date, nullable=True)
    
    # Legal pack fields
    legal_pack_analysis = db.Column(db.Text, nullable=True)
    legal_pack_qa_history = db.Column(db.Text, nullable=True)  # Store Q&A history as JSON
    legal_pack_summary_pdf = db.Column(db.String(500), nullable=True)  # Path to the PDF summary
    legal_pack_analyzed_at = db.Column(db.DateTime, nullable=True)
    legal_pack_session_id = db.Column(db.String(100), nullable=True)  # To link with legal doc analyzer session
    
    # Viewing dates fields
    viewing_date_1 = db.Column(db.DateTime, nullable=True)
    viewing_date_2 = db.Column(db.DateTime, nullable=True)
    viewing_date_3 = db.Column(db.DateTime, nullable=True)
    viewing_date_4 = db.Column(db.DateTime, nullable=True)
    
    # Calculated fields
    stamp_duty = db.Column(db.Float, nullable=True)
    total_purchase_fees = db.Column(db.Float, nullable=True)
    total_money_needed = db.Column(db.Float, nullable=True)
    cash_left_in_deal = db.Column(db.Float, nullable=True)
    annual_profit = db.Column(db.Float, nullable=True)
    total_roi = db.Column(db.Float, nullable=True)
    total_yield = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'rightmove_url': self.rightmove_url,
            'initial_cash': self.initial_cash,
            'purchase_price': self.purchase_price,
            'rooms': self.rooms,
            'monthly_rent': self.monthly_rent,
            'valuation_after': self.valuation_after,
            'renovation_cost': self.renovation_cost,
            'bridging_duration': self.bridging_duration,
            'void_period': self.void_period,
            'mortgage_ltv': self.mortgage_ltv,
            'mortgage_rate': self.mortgage_rate,
            'lender_fee': self.lender_fee,
            'bridging_rate': self.bridging_rate,
            'arrangement_rate': self.arrangement_rate,
            'broker_rate': self.broker_rate,
            'management_fee': self.management_fee,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'main_photo': self.main_photo,
            'floorplan': self.floorplan,
            'description': self.description,
            'key_features': json.loads(self.key_features) if self.key_features else [],
            'address': self.address,
            'is_auction': self.is_auction,
            'estate_agent': self.estate_agent,
            'nearest_station': self.nearest_station,
            'station_distance': self.station_distance,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'property_type': self.property_type,
            'legal_pack_url': self.legal_pack_url,
            'legal_pack_available': self.legal_pack_available,
            'risk_level': self.risk_level,
            'key_risks': self.key_risks,
            'extra_fees': self.extra_fees,
            'auction_date': self.auction_date.isoformat() if self.auction_date else None,
            'stamp_duty': self.stamp_duty,
            'total_purchase_fees': self.total_purchase_fees,
            'total_money_needed': self.total_money_needed,
            'cash_left_in_deal': self.cash_left_in_deal,
            'annual_profit': self.annual_profit,
            'total_roi': self.total_roi,
            'total_yield': self.total_yield,
            'legal_pack_analysis': self.legal_pack_analysis,
            'legal_pack_qa_history': json.loads(self.legal_pack_qa_history) if self.legal_pack_qa_history else [],
            'legal_pack_summary_pdf': self.legal_pack_summary_pdf,
            'legal_pack_analyzed_at': self.legal_pack_analyzed_at.isoformat() if self.legal_pack_analyzed_at else None,
            'legal_pack_session_id': self.legal_pack_session_id,
            'viewing_date_1': self.viewing_date_1.isoformat() if self.viewing_date_1 else None,
            'viewing_date_2': self.viewing_date_2.isoformat() if self.viewing_date_2 else None,
            'viewing_date_3': self.viewing_date_3.isoformat() if self.viewing_date_3 else None,
            'viewing_date_4': self.viewing_date_4.isoformat() if self.viewing_date_4 else None,
        }

# Create database and tables
def init_db():
    with app.app_context():
        # Drop all tables first
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Database initialized successfully!")

# Initialize database before running the app
init_db()

def extract_text_from_pdf(pdf_path):
    """Extract text content from a PDF file using both PyPDF2 and OCR if needed."""
    try:
        logger.info(f"Attempting to extract text from PDF: {pdf_path}")
        text = ""
        
        # First try PyPDF2
        with open(pdf_path, 'rb') as file:
            try:
                reader = PyPDF2.PdfReader(file)
                logger.info(f"Successfully created PDF reader. Number of pages: {len(reader.pages)}")
                
                for i, page in enumerate(reader.pages):
                    logger.info(f"Processing page {i+1}")
                    try:
                        page_text = page.extract_text()
                        
                        # If page has less than 100 characters or contains mostly whitespace,
                        # it might be scanned/image-based
                        if len(page_text.strip()) < 100 or len(page_text.strip()) / len(page_text) < 0.3:
                            logger.info(f"Page {i+1} appears to be scanned, attempting OCR")
                            # Convert PDF page to image with higher DPI for better OCR
                            images = convert_from_path(pdf_path, first_page=i+1, last_page=i+1, dpi=300)
                            if images:
                                # Perform OCR on the image with improved settings
                                page_text = pytesseract.image_to_string(
                                    images[0],
                                    config='--psm 1 --oem 3'  # Automatic page segmentation with LSTM OCR
                                )
                                logger.info(f"OCR completed for page {i+1}")
                        
                        text += page_text + '\n'
                        logger.info(f"Successfully processed page {i+1}. Text length: {len(page_text)}")
                    except Exception as e:
                        logger.error(f"Error processing page {i+1}: {str(e)}")
                        # Try OCR as fallback for failed pages
                        try:
                            images = convert_from_path(pdf_path, first_page=i+1, last_page=i+1, dpi=300)
                            if images:
                                page_text = pytesseract.image_to_string(
                                    images[0],
                                    config='--psm 1 --oem 3'
                                )
                                text += page_text + '\n'
                                logger.info(f"Successfully recovered page {i+1} using OCR")
                        except Exception as ocr_e:
                            logger.error(f"OCR recovery failed for page {i+1}: {str(ocr_e)}")
            except Exception as e:
                logger.error(f"PyPDF2 failed, attempting full document OCR: {str(e)}")
                # If PyPDF2 fails completely, try converting the entire document
                try:
                    images = convert_from_path(pdf_path, dpi=300)
                    for i, image in enumerate(images):
                        page_text = pytesseract.image_to_string(
                            image,
                            config='--psm 1 --oem 3'
                        )
                        text += page_text + '\n'
                        logger.info(f"Successfully processed page {i+1} with OCR")
                except Exception as ocr_e:
                    logger.error(f"Full document OCR failed: {str(ocr_e)}")
                    return None
        
        if not text.strip():
            logger.warning(f"No text content extracted from {pdf_path}")
            return None
            
        logger.info(f"Successfully extracted text from all pages. Total text length: {len(text)}")
        return text
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
        return None

def process_zip_file(zip_file_path):
    """Process a ZIP file and extract its contents."""
    processed_files = []
    failed_files = []
    processing_summary = []
    total_tokens = 0
    
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
            # Process each file in the zip
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.startswith('~'):  # Skip temporary files
                        continue
                        
                    file_path = os.path.join(root, file)
                    try:
                        content = process_document(file_path)
                        if content and content.strip():
                            num_tokens = count_tokens(content)
                            total_tokens += num_tokens
                            processed_files.append({
                                'name': file,
                                'content': content,
                                'length': len(content),
                                'tokens': num_tokens
                            })
                            processing_summary.append(f"Successfully processed {file} ({num_tokens} tokens)")
                        else:
                            failed_files.append(file)
                            processing_summary.append(f"Failed to extract content from {file}")
                    except Exception as e:
                        failed_files.append(file)
                        processing_summary.append(f"Error processing {file}: {str(e)}")
                        logger.error(f"Error processing {file}: {str(e)}")

    # Save processing results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "documents": processed_files,  # Save the full array of processed files
        "failed_files": failed_files,
        "processed_at": datetime.now().isoformat(),
        "total_documents": len(processed_files) + len(failed_files),
        "total_tokens": total_tokens,
        "processing_summary": processing_summary
    }
    
    results_filename = f"processing_results_{timestamp}.json"
    results_filepath = STORAGE_DIR / results_filename
    
    with open(results_filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Processing results saved to {results_filepath}")
    logger.info(f"Total tokens across all documents: {total_tokens}")
    
    return processed_files, failed_files, "\n".join(processing_summary)

def process_document(file_path):
    """Process a single document and return its text content."""
    try:
        _, ext = os.path.splitext(file_path.lower())
        
        if ext == '.pdf':
            return extract_text_from_pdf(file_path)
        elif ext == '.docx':
            try:
                doc = Document(file_path)
                return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            except Exception as e:
                logger.error(f"Error processing DOCX file {file_path}: {str(e)}")
                return None
        elif ext == '.doc':
            logger.warning(f"Old .doc format detected for {file_path}. Converting to PDF first...")
            try:
                # Convert .doc to PDF using LibreOffice (if available)
                pdf_path = file_path + '.pdf'
                result = subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', 
                                      os.path.dirname(file_path), file_path], 
                                     capture_output=True, text=True)
                if os.path.exists(pdf_path):
                    text = extract_text_from_pdf(pdf_path)
                    os.remove(pdf_path)  # Clean up temporary PDF
                    return text
                else:
                    logger.error(f"Failed to convert .doc to PDF: {result.stderr}")
                    return None
            except Exception as e:
                logger.error(f"Error converting .doc file {file_path}: {str(e)}")
                return None
        elif ext == '.txt':
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            except UnicodeDecodeError:
                # Try different encodings if utf-8 fails
                encodings = ['latin-1', 'cp1252', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as file:
                            return file.read()
                    except UnicodeDecodeError:
                        continue
                logger.error(f"Could not decode file {file_path} with any known encoding")
                return None
        else:
            logger.warning(f"Unsupported file type: {ext} for file {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        return None

def save_documents(session_id, processed_files, initial_analysis=None, qa_history=None):
    """Save documents and analysis history to disk."""
    try:
        # Ensure the storage directory exists with proper permissions
        STORAGE_DIR.mkdir(mode=0o777, parents=True, exist_ok=True)
        
        file_path = STORAGE_DIR / f"{session_id}.json"
        data = {
            'documents': processed_files,  # Save the full array of processed files
            'initial_analysis': initial_analysis,
            'qa_history': qa_history or []
        }
        
        # Write the file with explicit encoding
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        # Set file permissions
        os.chmod(file_path, 0o666)
        
        return True
    except Exception as e:
        logger.error(f"Error saving documents: {str(e)}")
        return False

def load_documents(session_id):
    """Load documents and analysis history from disk."""
    try:
        file_path = STORAGE_DIR / f"{session_id}.json"
        if not file_path.exists():
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return data['documents'], data['initial_analysis'], data['qa_history']
    except Exception as e:
        logger.error(f"Error loading documents: {str(e)}")
        return None

def analyze_with_claude(documents_content, processing_summary=None, follow_up_question=None, initial_analysis=None, qa_history=None):
    try:
        client = anthropic.Anthropic(api_key=os.getenv('CLAUDE_API_KEY'))
        
        # Prepare the system prompt
        system_prompt = """You are a legal expert analyzing property documents. Focus on:
1. Key risks and issues
2. Important dates and deadlines
3. Financial obligations
4. Legal restrictions
5. Property boundaries and rights
Provide a clear, concise summary highlighting any red flags."""

        # Prepare the user message
        user_message = "Please analyze these property documents:\n\n"
        for doc in documents_content:
            user_message += f"Document: {doc['name']}\n{doc['content']}\n\n"
        
        if follow_up_question:
            user_message = f"Based on the documents above, please answer: {follow_up_question}"
            if qa_history:
                user_message += f"\n\nPrevious Q&A:\n{qa_history}"

        # Create the message using the new API format
        response = client.messages.create(
            model="claude-3-opus-20240229",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=4000
        )

        # Extract the response
        analysis = response.content[0].text

        app.logger.info(f"Successfully got analysis from Claude API")
        return analysis

    except Exception as e:
        error_msg = f"Failed to get analysis from Claude API: {str(e)}"
        app.logger.error(error_msg)
        raise Exception(error_msg)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/calculator_test')
def calculator():
    property_id = request.args.get('id')
    if property_id:
        property = Property.query.get_or_404(property_id)
        return render_template('calculator_test.html', property=property.to_dict())
    return render_template('calculator_test.html')

@app.route('/property/<int:property_id>')
def property_details(property_id):
    property = Property.query.get_or_404(property_id)
    return render_template('calculator_test.html', property=property.to_dict())

@app.route('/api/properties/<int:property_id>', methods=['DELETE'])
def delete_property(property_id):
    try:
        property = Property.query.get_or_404(property_id)
        db.session.delete(property)
        db.session.commit()
        return jsonify({'message': 'Property deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/properties/<int:property_id>', methods=['PUT'])
def update_property(property_id):
    try:
        data = request.get_json()
        property = Property.query.get_or_404(property_id)
        
        # Update property fields
        property.rightmove_url = data.get('rightmove_url')
        property.initial_cash = data.get('initial_cash')
        property.purchase_price = data.get('purchase_price')
        property.rooms = data.get('rooms')
        property.monthly_rent = data.get('monthly_rent')
        property.valuation_after = data.get('valuation_after')
        property.renovation_cost = data.get('renovation_cost')
        property.bridging_duration = data.get('bridging_duration')
        property.void_period = data.get('void_period')
        property.mortgage_ltv = data.get('mortgage_ltv')
        property.mortgage_rate = data.get('mortgage_rate')
        property.lender_fee = data.get('lender_fee')
        property.bridging_rate = data.get('bridging_rate')
        property.arrangement_rate = data.get('arrangement_rate')
        property.broker_rate = data.get('broker_rate')
        property.management_fee = data.get('management_fee')
        property.main_photo = data.get('main_photo')
        property.floorplan = data.get('floorplan')
        property.description = data.get('description')
        property.estate_agent = data.get('estate_agent')
        property.nearest_station = data.get('nearest_station')
        property.station_distance = data.get('station_distance')
        property.bedrooms = data.get('bedrooms')
        property.bathrooms = data.get('bathrooms')
        property.property_type = data.get('property_type')
        property.legal_pack_url = data.get('legal_pack_url')
        property.risk_level = data.get('risk_level')
        property.key_risks = data.get('key_risks')
        property.extra_fees = data.get('extra_fees')
        property.auction_date = datetime.strptime(data['auction_date'], '%Y-%m-%d').date() if data.get('auction_date') else None
        
        # Update viewing dates
        property.viewing_date_1 = datetime.fromisoformat(data['viewing_date_1'].replace('Z', '+00:00')) if data.get('viewing_date_1') else None
        property.viewing_date_2 = datetime.fromisoformat(data['viewing_date_2'].replace('Z', '+00:00')) if data.get('viewing_date_2') else None
        property.viewing_date_3 = datetime.fromisoformat(data['viewing_date_3'].replace('Z', '+00:00')) if data.get('viewing_date_3') else None
        property.viewing_date_4 = datetime.fromisoformat(data['viewing_date_4'].replace('Z', '+00:00')) if data.get('viewing_date_4') else None
        
        # Update calculated fields
        property.stamp_duty = data.get('stamp_duty')
        property.total_purchase_fees = data.get('total_purchase_fees')
        property.total_money_needed = data.get('total_money_needed')
        property.cash_left_in_deal = data.get('cash_left_in_deal')
        property.annual_profit = data.get('annual_profit')
        property.total_roi = data.get('total_roi')
        property.total_yield = data.get('total_yield')
        
        db.session.commit()
        return jsonify(property.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/properties/<int:property_id>/duplicate', methods=['POST'])
def duplicate_property(property_id):
    try:
        # Get the original property
        original = Property.query.get_or_404(property_id)
        
        # Create a new property with the same data
        new_property = Property(
            rightmove_url=original.rightmove_url,
            initial_cash=original.initial_cash,
            purchase_price=original.purchase_price,
            rooms=original.rooms,
            monthly_rent=original.monthly_rent,
            valuation_after=original.valuation_after,
            renovation_cost=original.renovation_cost,
            bridging_duration=original.bridging_duration,
            void_period=original.void_period,
            mortgage_ltv=original.mortgage_ltv,
            mortgage_rate=original.mortgage_rate,
            lender_fee=original.lender_fee,
            bridging_rate=original.bridging_rate,
            arrangement_rate=original.arrangement_rate,
            broker_rate=original.broker_rate,
            management_fee=original.management_fee,
            main_photo=original.main_photo,
            floorplan=original.floorplan,
            description=original.description,
            key_features=original.key_features,
            address=f"{original.address} (Copy)",
            is_auction=original.is_auction,
            estate_agent=original.estate_agent,
            nearest_station=original.nearest_station,
            station_distance=original.station_distance,
            bedrooms=original.bedrooms,
            bathrooms=original.bathrooms,
            property_type=original.property_type,
            legal_pack_url=original.legal_pack_url,
            legal_pack_available=original.legal_pack_available,
            risk_level=original.risk_level,
            key_risks=original.key_risks,
            extra_fees=original.extra_fees,
            auction_date=original.auction_date,
            stamp_duty=original.stamp_duty,
            total_purchase_fees=original.total_purchase_fees,
            total_money_needed=original.total_money_needed,
            cash_left_in_deal=original.cash_left_in_deal,
            annual_profit=original.annual_profit,
            total_roi=original.total_roi,
            total_yield=original.total_yield,
            legal_pack_analysis=original.legal_pack_analysis,
            legal_pack_qa_history=original.legal_pack_qa_history,
            legal_pack_summary_pdf=original.legal_pack_summary_pdf,
            legal_pack_analyzed_at=original.legal_pack_analyzed_at,
            legal_pack_session_id=original.legal_pack_session_id
        )
        
        db.session.add(new_property)
        db.session.commit()
        
        return jsonify({'message': 'Property duplicated successfully', 'id': new_property.id})
    except Exception as e:
        return jsonify({'error': f'Failed to duplicate property: {str(e)}'}), 500

@app.route('/test-property-details')
def test_property_details():
    # Sample property data for testing
    test_property = {
        'main_photo': 'https://media.rightmove.co.uk/dir/crop/10:9-16:9/108k/107051/128095236/107051_11261955_IMG_00_0000_max_476x317.jpeg',
        'floorplan': 'https://media.rightmove.co.uk/dir/108k/107051/128095236/107051_11261955_FLP_00_0000_max_600x600.jpeg',
        'address': '123 Test Street, London',
        'description': 'A beautiful test property with modern amenities and great location.',
        'bedrooms': 3,
        'bathrooms': 2,
        'property_type': 'Semi-Detached',
        'station_distance': '0.5',
        'key_features': [
            'Modern Kitchen',
            'Large Garden',
            'Recently Renovated',
            'Close to Schools'
        ],
        'purchase_price': 250000,
        'legal_fees': 1500,
        'survey_costs': 800,
        'refurb_costs': 15000,
        'contingency': 5000,
        'bridging_loan_amount': 200000,
        'bridging_loan_term': 6,
        'bridging_loan_rate': 0.89,
        'mortgage_amount': 187500,
        'mortgage_term': 25,
        'mortgage_rate': 4.5,
        'rental_income': 1500
    }
    return render_template('property_details.html', property=test_property)

@app.route('/api/properties', methods=['GET'])
def get_properties():
    try:
        properties = Property.query.order_by(Property.created_at.desc()).all()
        return jsonify([p.to_dict() for p in properties])
    except Exception as e:
        print("Error fetching properties:", str(e))
        return jsonify({'error': 'Failed to fetch properties', 'details': str(e)}), 500

@app.route('/api/properties', methods=['POST'])
def create_property():
    try:
        data = request.get_json()
        
        # Handle auction_date - set to None if empty string or invalid
        auction_date = None
        if data.get('auction_date'):
            if isinstance(data['auction_date'], str) and data['auction_date'].strip():
                try:
                    auction_date = datetime.strptime(data['auction_date'], '%Y-%m-%d').date()
                except ValueError:
                    auction_date = None

        # Convert key_features to JSON string if it's a list
        key_features = data.get('key_features', [])
        if isinstance(key_features, list):
            key_features = json.dumps(key_features)
        elif key_features is None:
            key_features = json.dumps([])

        property = Property(
            rightmove_url=data.get('rightmove_url'),
            initial_cash=data.get('initial_cash'),
            purchase_price=data.get('purchase_price'),
            rooms=data.get('rooms'),
            monthly_rent=data.get('monthly_rent'),
            valuation_after=data.get('valuation_after'),
            renovation_cost=data.get('renovation_cost'),
            bridging_duration=data.get('bridging_duration'),
            void_period=data.get('void_period'),
            mortgage_ltv=data.get('mortgage_ltv'),
            mortgage_rate=data.get('mortgage_rate'),
            lender_fee=data.get('lender_fee'),
            bridging_rate=data.get('bridging_rate'),
            arrangement_rate=data.get('arrangement_rate'),
            broker_rate=data.get('broker_rate'),
            management_fee=data.get('management_fee'),
            created_at=datetime.now(),
            main_photo=data.get('main_photo'),
            floorplan=data.get('floorplan'),
            description=data.get('description'),
            key_features=key_features,
            address=data.get('address'),
            is_auction=data.get('is_auction', False),
            estate_agent=data.get('estate_agent'),
            nearest_station=data.get('nearest_station'),
            station_distance=data.get('station_distance'),
            bedrooms=data.get('bedrooms'),
            bathrooms=data.get('bathrooms'),
            property_type=data.get('property_type'),
            legal_pack_url=data.get('legal_pack_url'),
            legal_pack_available=data.get('legal_pack_available', False),
            risk_level=data.get('risk_level'),
            key_risks=data.get('key_risks'),
            extra_fees=data.get('extra_fees', 0),
            auction_date=auction_date,
            stamp_duty=data.get('stamp_duty'),
            total_purchase_fees=data.get('total_purchase_fees'),
            total_money_needed=data.get('total_money_needed'),
            cash_left_in_deal=data.get('cash_left_in_deal'),
            annual_profit=data.get('annual_profit'),
            total_roi=data.get('total_roi'),
            total_yield=data.get('total_yield'),
            legal_pack_analysis=data.get('legal_pack_analysis'),
            legal_pack_qa_history=data.get('legal_pack_qa_history'),
            legal_pack_summary_pdf=data.get('legal_pack_summary_pdf'),
            legal_pack_analyzed_at=data.get('legal_pack_analyzed_at'),
            legal_pack_session_id=data.get('legal_pack_session_id'),
            viewing_date_1=datetime.fromisoformat(data['viewing_date_1'].replace('Z', '+00:00')) if data.get('viewing_date_1') else None,
            viewing_date_2=datetime.fromisoformat(data['viewing_date_2'].replace('Z', '+00:00')) if data.get('viewing_date_2') else None,
            viewing_date_3=datetime.fromisoformat(data['viewing_date_3'].replace('Z', '+00:00')) if data.get('viewing_date_3') else None,
            viewing_date_4=datetime.fromisoformat(data['viewing_date_4'].replace('Z', '+00:00')) if data.get('viewing_date_4') else None,
        )
        
        db.session.add(property)
        db.session.commit()
        
        return jsonify(property.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        print("Error details:", str(e))
        return jsonify({'error': 'Failed to create property', 'details': str(e)}), 400

@app.route('/scrape-property', methods=['POST'])
def scrape_property():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    scraper = PropertyScraper()
    try:
        # Run the async scraping in the event loop
        result = asyncio.run(scraper.scrape_rightmove(url))
        if result:
            return jsonify(result), 200
        return jsonify({'error': 'Failed to scrape property data'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/toggle_auction/<int:property_id>', methods=['POST'])
def toggle_auction(property_id):
    try:
        data = request.get_json()
        property = Property.query.get_or_404(property_id)
        property.is_auction = data['is_auction']
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/legal-pack-analyzer/<int:property_id>')
def legal_pack_analyzer(property_id):
    """Render the legal pack analyzer page for a specific property."""
    # Get the property details if needed
    property_data = Property.query.get_or_404(property_id)
    return render_template('legal_pack_analyzer.html', property=property_data, property_id=property_id)

@app.route('/analyze-legal-pack', methods=['POST'])
def analyze_legal_pack():
    """Handle legal pack file upload and analysis."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded', 'suggestion': 'Please select a file to upload'}), 400
        
        file = request.files['file']
        property_id = request.form.get('property_id')
        
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected', 'suggestion': 'Please select a file to upload'}), 400
            
        if not property_id:
            return jsonify({'error': 'No property ID provided', 'suggestion': 'Please try again or contact support'}), 400
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, filename)
        file.save(zip_path)
        
        try:
            # First process all documents and collect results
            processed_files, failed_files, processing_summary = process_zip_file(zip_path)
            
            if not processed_files:
                return jsonify({
                    'error': 'No documents could be processed',
                    'suggestion': 'Please check that the ZIP file contains valid documents'
                }), 400
            
            # Generate a session ID for this analysis
            session_id = str(uuid.uuid4())
            
            # Save the processed documents
            save_documents(session_id, processed_files)
            
            # Calculate total tokens
            total_tokens = sum(doc['tokens'] for doc in processed_files)
            logger.info(f"Total tokens before analysis: {total_tokens}")
            
            # Only proceed with analysis if we have all documents processed
            analysis_result = analyze_with_claude(processed_files, processing_summary)
            
            # Save documents and initial analysis
            save_documents(session_id, processed_files, analysis_result)
            
            # Update property with analysis and session ID
            property = Property.query.get(property_id)
            if property:
                property.legal_pack_analysis = analysis_result
                property.legal_pack_session_id = session_id
                property.legal_pack_analyzed_at = datetime.utcnow()
                db.session.commit()
            
            return jsonify({
                'analysis': analysis_result,
                'session_id': session_id,
                'processing_summary': processing_summary,
                'total_tokens': total_tokens,
                'total_documents': len(processed_files),
                'failed_documents': len(failed_files)
            })
            
        finally:
            # Clean up temporary files
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        logger.error(f"Error in analyze_legal_pack: {str(e)}")
        return jsonify({
            'error': 'Failed to analyze documents',
            'suggestion': 'Please try again or contact support if the problem persists',
            'details': str(e)
        }), 500

@app.route('/property/ask_followup', methods=['POST'])
def ask_followup():
    """Handle follow-up questions about the legal pack."""
    try:
        data = request.get_json()
        question = data.get('question')
        session_id = data.get('session_id')
        property_id = data.get('property_id')
        
        logger.info(f"Received follow-up question request: {data}")
        
        if not all([question, session_id, property_id]):
            missing = []
            if not question: missing.append('question')
            if not session_id: missing.append('session_id')
            if not property_id: missing.append('property_id')
            error_msg = f"Missing required information: {', '.join(missing)}"
            logger.error(error_msg)
            return jsonify({
                'error': error_msg,
                'suggestion': 'Please provide all required information'
            }), 400
        
        # Load the documents and previous analysis
        try:
            documents, initial_analysis, qa_history = load_documents(session_id)
            logger.info(f"Loaded documents for session {session_id}")
            logger.info(f"Number of documents: {len(documents) if documents else 0}")
            logger.info(f"Initial analysis length: {len(initial_analysis) if initial_analysis else 0}")
            logger.info(f"QA history length: {len(qa_history) if qa_history else 0}")
        except Exception as e:
            error_msg = f"Failed to load documents: {str(e)}"
            logger.error(error_msg)
            return jsonify({
                'error': error_msg,
                'suggestion': 'Please try uploading the documents again'
            }), 500
        
        if not documents:
            error_msg = "No documents found for this session"
            logger.error(error_msg)
            return jsonify({
                'error': error_msg,
                'suggestion': 'Please upload the documents again'
            }), 404
            
        if not initial_analysis:
            error_msg = "No initial analysis found for this session"
            logger.error(error_msg)
            return jsonify({
                'error': error_msg,
                'suggestion': 'Please perform initial analysis first'
            }), 404
        
        # Get answer from Claude
        try:
            result = analyze_with_claude(
                documents,
                follow_up_question=question,
                initial_analysis=initial_analysis,
                qa_history=qa_history
            )
            logger.info("Successfully got answer from Claude")
        except Exception as e:
            error_msg = f"Failed to get answer from Claude: {str(e)}"
            logger.error(error_msg)
            return jsonify({
                'error': error_msg,
                'suggestion': 'Please try again or contact support if the problem persists'
            }), 500
        
        if not result:
            error_msg = "Invalid response format from analysis"
            logger.error(f"{error_msg}: {result}")
            return jsonify({
                'error': error_msg,
                'suggestion': 'Please try again or contact support'
            }), 500
        
        # Update QA history
        try:
            qa_history = qa_history or []
            qa_history.append({
                'question': question,
                'answer': result
            })
            # Save to document storage
            save_documents(session_id, documents, initial_analysis, qa_history)
            
            # Save to property database
            property = Property.query.get(property_id)
            if property:
                property.legal_pack_qa_history = json.dumps(qa_history)
                db.session.commit()
                
            logger.info("Successfully updated QA history in both storage and database")
        except Exception as e:
            # Log the error but don't fail the request
            logger.error(f"Failed to update QA history: {str(e)}")
        
        return jsonify({
            'answer': result
        })
            
    except Exception as e:
        error_msg = f"Unexpected error in ask_followup: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            'error': error_msg,
            'suggestion': 'Please try again or contact support if the problem persists'
        }), 500

@app.route('/system-check', methods=['GET'])
def system_check():
    """Check system dependencies and configuration."""
    import subprocess
    import shutil
    
    status = {
        'tesseract': False,
        'libreoffice': False,
        'environment': {
            'CLAUDE_API_KEY': bool(os.getenv('CLAUDE_API_KEY')),
            'DATABASE_URL': bool(os.getenv('DATABASE_URL'))
        },
        'anthropic_version': anthropic.__version__
    }
    
    # Check tesseract
    tesseract_path = shutil.which('tesseract')
    status['tesseract'] = bool(tesseract_path)
    
    # Check libreoffice
    soffice_path = shutil.which('soffice')
    status['libreoffice'] = bool(soffice_path)
    
    return jsonify(status)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5004)
else:
    # This ensures tables are created when running on Render
    with app.app_context():
        db.create_all()
