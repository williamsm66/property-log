import os
import time
import logging
from urllib.parse import urljoin
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import logging
import http.cookiejar
from urllib.parse import quote, urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
import time
import re

# Initialize Flask app with custom template folder
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
CORS(app)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///legal_documents.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s:%(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('legal_docs_app.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Document storage path
STORAGE_PATH = os.path.join(os.path.dirname(__file__), 'storage', 'documents')
os.makedirs(STORAGE_PATH, exist_ok=True)

class LegalDocument(db.Model):
    __tablename__ = 'legal_documents'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, nullable=True)
    document_type = db.Column(db.String(100))
    filename = db.Column(db.String(255))
    local_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    download_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_analyzed_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='pending')
    source_url = db.Column(db.String(500))
    
    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
            'document_type': self.document_type,
            'filename': self.filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'download_date': self.download_date.isoformat() if self.download_date else None,
            'last_analyzed_date': self.last_analyzed_date.isoformat() if self.last_analyzed_date else None,
            'status': self.status,
            'source_url': self.source_url
        }

class DocumentAnalysis(db.Model):
    __tablename__ = 'document_analyses'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, nullable=True)
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)
    anthropic_response = db.Column(db.Text)
    identified_risks = db.Column(db.Text)
    confidence_score = db.Column(db.Float)

class DocumentService:
    def __init__(self):
        # Initialize Chrome options
        self.driver = None
        self.base_storage_path = STORAGE_PATH
        
    def _init_driver(self):
        """Initialize Chrome driver with options"""
        try:
            chrome_options = Options()
            # chrome_options.add_argument('--headless')  # Commented out for debugging
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            logger.info("Initializing Chrome driver...")
            self.driver = webdriver.Chrome(options=chrome_options)
            if not self.driver:
                logger.error("Chrome driver initialization returned None")
                return False
            
            logger.info("Chrome driver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Chrome driver: {str(e)}")
            self.driver = None
            return False

    def _quit_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def authenticate(self, username, password, return_url=None):
        """Authenticate with EI Group using Selenium"""
        logger.info("\n=== URL TRACKING LOG ===")
        logger.info(f"1. Target document URL we want to reach: {return_url}")
        
        try:
            success = self._init_driver()
            if not success:
                logger.error("Failed to initialize Chrome driver")
                return False
                
            if not self.driver:
                logger.error("Driver is None after initialization")
                return False
                
            wait = WebDriverWait(self.driver, 10)
            
            # Go to login page
            login_url = "https://legaldocuments.eigroup.co.uk/account/login"
            if return_url:
                encoded_return_url = quote(return_url)
                login_url += f"?ReturnUrl={encoded_return_url}"
            
            logger.info(f"2. Full login URL with return parameter: {login_url}")
            
            try:
                self.driver.get(login_url)
                logger.info(f"3. Actually landed on URL: {self.driver.current_url}")
                logger.info(f"4. Page title on landing: {self.driver.title}")
                
                # Wait for and fill in the login form
                logger.info("Looking for login form...")
                email_field = wait.until(EC.presence_of_element_located((By.ID, "Email")))
                password_field = self.driver.find_element(By.ID, "Password")
                
                email_field.send_keys(username)
                password_field.send_keys(password)
                
                # Find and click the login button
                login_button = None
                selectors = [
                    "input[type='submit'][value='Sign In']",
                    "input[type='submit'][value='Log In']",
                    "input[type='submit'].btn.btn-primary",
                    "button[type='submit']"
                ]
                
                for selector in selectors:
                    try:
                        login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if login_button:
                            logger.info(f"Found login button with selector: {selector}")
                            break
                    except:
                        continue
                
                if not login_button:
                    logger.error("Could not find login button")
                    return False
                
                logger.info("Clicking login button...")
                login_button.click()
                
                # Wait for redirect
                time.sleep(2)
                
                # Log post-login state
                logger.info(f"5. URL after clicking login: {self.driver.current_url}")
                logger.info(f"6. Page title after login: {self.driver.title}")
                
                # Check if we're still on login page
                if "login" in self.driver.current_url.lower():
                    logger.error("Still on login page after clicking login button")
                    return False
                
                # Check if we reached target URL
                if return_url:
                    logger.info(f"7. Checking if we reached target URL...")
                    logger.info(f"   Expected: {return_url}")
                    logger.info(f"   Current:  {self.driver.current_url}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error during login process: {str(e)}")
                if self.driver:
                    logger.error(f"Current URL when error occurred: {self.driver.current_url}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
        finally:
            logger.info("=== END URL TRACKING LOG ===\n")

    def fetch_documents(self, url, username, password):
        """Fetch documents using Selenium"""
        try:
            if not self.authenticate(username, password, return_url=url):
                print("Authentication failed")
                return False
                
            # Now we should be on the documents page
            print(f"Fetching documents from: {url}")
            
            if url != self.driver.current_url:
                print(f"Navigating to documents page: {url}")
                self.driver.get(url)
                # Wait longer after navigation to final page
                print("Waiting 15 seconds for page to fully load...")
                time.sleep(15)
            
            # Wait for the page to load
            wait = WebDriverWait(self.driver, 20)
            
            # Wait for document table to be present
            print("Waiting for document table...")
            try:
                # First wait for the body to be present
                print("Waiting for body...")
                body = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                print("Body found")
                
                # Print current URL and title for debugging
                print(f"Current URL: {self.driver.current_url}")
                print(f"Page title: {self.driver.title}")
                
                # Take a screenshot before looking for table
                print("Taking screenshot...")
                self.driver.save_screenshot("before_table.png")
                
                # Wait for the document table
                print("Looking for eig-div-table...")
                table = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "eig-div-table")))
                print("Document table found")
                
                # Wait for document rows to be present
                print("Looking for data-row elements...")
                rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-row]")))
                print(f"Found {len(rows)} document rows")
                
                # Additional wait after finding elements
                print("Waiting 5 more seconds for dynamic content...")
                time.sleep(5)
                
                documents = []
                for idx, row in enumerate(rows):
                    try:
                        # Find the download link in this row
                        print(f"Processing row {idx + 1}...")
                        link = row.find_element(By.CSS_SELECTOR, "a[href*='downloaddocument']")
                        doc_name = link.text.strip()
                        doc_url = link.get_attribute('href')
                        
                        # Extract document details
                        doc_info = {
                            'name': doc_name,
                            'url': doc_url,
                            'downloaded': False
                        }
                        documents.append(doc_info)
                        print(f"Found document: {doc_name}")
                    except Exception as e:
                        print(f"Error processing row {idx + 1}: {str(e)}")
                        continue
                
                print(f"Total documents found: {len(documents)}")
                return documents
                
            except TimeoutException as e:
                print(f"Timeout waiting for elements: {str(e)}")
                # Take a screenshot for debugging
                self.driver.save_screenshot("debug_timeout.png")
                # Log the page source
                print("Page source at timeout:")
                print(self.driver.page_source[:500] + "...")  # Print first 500 chars
                return []
                
        except Exception as e:
            print(f"Error in fetch_documents: {str(e)}")
            return []

# Initialize document service
document_service = DocumentService()

@app.route('/')
@app.route('/legal-documents')
def legal_documents():
    return render_template('legal_documents.html')

@app.route('/api/documents/fetch', methods=['POST'])
def fetch_documents():
    data = request.get_json()
    
    # Log incoming request data (excluding password)
    safe_data = {k: v for k, v in data.items() if k != 'password'}
    logger.info(f"Received document fetch request: {safe_data}")
    
    # Validate required fields
    required_fields = ['url', 'username', 'password']
    missing_fields = [field for field in required_fields if not data.get(field)]
    
    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        logger.error(error_msg)
        return jsonify({'status': 'error', 'message': error_msg}), 400
    
    try:
        # Call document service to fetch documents
        documents = document_service.fetch_documents(
            data['url'],
            data['username'],
            data['password']
        )
        
        if documents is False:
            return jsonify({
                'status': 'error',
                'message': 'Failed to fetch documents. Check logs for details.',
                'documents': []
            }), 500
            
        # Get the current page title
        page_title = document_service.driver.title if document_service.driver else "Unknown"
        current_url = document_service.driver.current_url if document_service.driver else data['url']
        
        return jsonify({
            'status': 'success',
            'message': f'Found {len(documents)} documents',
            'documents': documents,
            'page_title': page_title,
            'current_url': current_url
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}',
            'documents': []
        }), 500

@app.route('/api/documents', methods=['GET'])
def get_documents():
    documents = LegalDocument.query.all()
    return jsonify({'documents': [doc.to_dict() for doc in documents]})

@app.route('/api/documents/<int:document_id>/download', methods=['GET'])
def download_document(document_id):
    document = LegalDocument.query.get_or_404(document_id)
    if not document.local_path or not os.path.exists(document.local_path):
        return jsonify({'error': 'Document file not found'}), 404
    
    return send_file(document.local_path, 
                    mimetype=document.mime_type,
                    as_attachment=True,
                    download_name=document.filename)

@app.route('/test-auth', methods=['POST'])
def test_auth():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    logger.info(f"Testing authentication for user: {username}")
    
    if document_service.authenticate(username, password):
        return jsonify({"status": "success", "message": "Authentication successful"})
    else:
        return jsonify({"status": "error", "message": "Authentication failed"}), 401

@app.route('/test-login')
def test_login():
    return '''
    <html>
        <body>
            <h2>Test Login</h2>
            <form id="loginForm">
                <div>
                    <label>Username:</label>
                    <input type="text" id="username" name="username">
                </div>
                <div style="margin-top: 10px;">
                    <label>Password:</label>
                    <input type="password" id="password" name="password">
                </div>
                <div style="margin-top: 10px;">
                    <button type="submit">Login</button>
                </div>
                <div id="result" style="margin-top: 10px;"></div>
            </form>
            <script>
                document.getElementById('loginForm').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const username = document.getElementById('username').value;
                    const password = document.getElementById('password').value;
                    const result = document.getElementById('result');
                    
                    try {
                        const response = await fetch('/test-auth', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ username, password })
                        });
                        const data = await response.json();
                        result.textContent = data.message;
                        result.style.color = response.ok ? 'green' : 'red';
                    } catch (error) {
                        result.textContent = 'Error: ' + error.message;
                        result.style.color = 'red';
                    }
                });
            </script>
        </body>
    </html>
    '''

@app.route('/test-docs')
def test_docs():
    return render_template('test_docs.html')

@app.route('/test-fetch', methods=['POST'])
def test_fetch():
    try:
        data = request.get_json()
        if not data:
            logger.error("No JSON data received in request")
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            logger.error("Missing username or password")
            return jsonify({"status": "error", "message": "Username and password are required"}), 400
        
        logger.info(f"Testing document fetch for user: {username}")
        
        # Document page URL
        doc_url = "https://legaldocuments.eigroup.co.uk/showbyid/1273139"
        logger.info(f"\nStarting document fetch process...")
        logger.info(f"Target document URL: {doc_url}")
        
        try:
            # First authenticate with the return URL
            auth_success = document_service.authenticate(username, password, return_url=doc_url)
            if not auth_success:
                logger.error("Authentication failed")
                return jsonify({"status": "error", "message": "Authentication failed"}), 401
            
            # Try to fetch the document page
            logger.info(f"Authentication successful, fetching document page: {doc_url}")
            
            if not document_service.driver:
                logger.error("Driver is None after authentication")
                return jsonify({"status": "error", "message": "Browser initialization failed"}), 500
                
            document_service.driver.get(doc_url)
            current_url = document_service.driver.current_url
            logger.info(f"Document page URL after navigation: {current_url}")
            
            # Parse the page to find document links
            page_source = document_service.driver.page_source
            if not page_source:
                logger.error("Could not get page source")
                return jsonify({"status": "error", "message": "Could not load document page"}), 500
                
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Log the page structure
            title = soup.title.string if soup.title else 'No title'
            logger.info(f"Page title: {title}")
            
            # Find all document links and their details
            documents = []
            rows = soup.find_all('tr')  # Find all table rows
            
            for row in rows:
                try:
                    # Get document link and name
                    link_elem = row.find('a')
                    if not link_elem:
                        continue
                        
                    doc_link = link_elem.get('href')
                    doc_name = link_elem.text.strip()
                    
                    # Get other columns
                    columns = row.find_all('td')
                    if len(columns) >= 4:  # We expect Document, File Size, Last Updated, Downloaded, Actions
                        file_size = columns[1].text.strip() if len(columns) > 1 else 'Unknown'
                        last_updated = columns[2].text.strip() if len(columns) > 2 else 'Unknown'
                        downloaded_status = columns[3].text.strip() if len(columns) > 3 else 'Unknown'
                        
                        documents.append({
                            'name': doc_name,
                            'link': doc_link,
                            'file_size': file_size,
                            'last_updated': last_updated,
                            'status': downloaded_status
                        })
                except Exception as e:
                    logger.warning(f"Error parsing document row: {str(e)}")
                    continue
            
            logger.info(f"Found {len(documents)} documents:")
            for doc in documents:
                logger.info(f"- {doc['name']} ({doc['file_size']}) - Last updated: {doc['last_updated']}")
            
            return jsonify({
                "status": "success",
                "message": f"Found {len(documents)} documents",
                "page_title": title,
                "current_url": current_url,
                "documents": documents
            })
            
        except Exception as e:
            logger.error(f"Error during document fetch: {str(e)}")
            return jsonify({"status": "error", "message": f"Document fetch error: {str(e)}"}), 500
        finally:
            if document_service.driver:
                document_service._quit_driver()
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

@app.route('/analyze-legal-pack', methods=['POST'])
def analyze_legal_pack():
    try:
        data = request.get_json()
        url = data.get('url')
        property_id = data.get('property_id')

        if not url:
            return jsonify({'error': 'No URL provided'}), 400

        # Initialize the document service
        document_service = DocumentService()

        try:
            # Fetch and analyze the documents
            documents = document_service.fetch_documents(url, None, None)  # No auth needed for public docs
            
            if not documents:
                return jsonify({'error': 'No documents found at the provided URL'}), 404

            # Process the documents
            all_content = []
            for doc in documents:
                if doc.local_path and os.path.exists(doc.local_path):
                    with open(doc.local_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        all_content.append(f"Document: {doc.filename}\n\n{content}\n\n")

            # Analyze with Claude
            client = anthropic.Anthropic(api_key=os.getenv('CLAUDE_API_KEY'))
            
            prompt = f"""As a conveyancer, please provide a comprehensive analysis of this legal pack for an auction property. 

            CRITICAL INSTRUCTIONS:
            - DO NOT make any assumptions about information that isn't explicitly stated in the legal pack
            - DO NOT imply or guess at potential issues that aren't clearly documented
            - When information is missing or unclear, state "INFORMATION NOT FOUND IN LEGAL PACK: [specify what's missing]"
            - If a section cannot be fully analyzed due to missing information, state "INCOMPLETE INFORMATION: Further investigation required for [specify area]"
            - Only state facts that are directly evidenced in the provided documents
            - For any risk mentioned, cite the specific document and section where it was found

            Structure the analysis around these key areas:

            1. AUCTION PURCHASE CONSIDERATIONS
            - Required deposit and payment terms
            - Completion timeframe and requirements
            - All auction fees and additional costs (including hidden fees)
            - Any special auction conditions
            - Required pre-auction searches or surveys
            - Insurance requirements from auction date

            2. PROPERTY LEGAL STATUS
            Analyze and detail any issues with:
            - Title type and any title defects
            - Outstanding liens or charges
            - Restrictive covenants and their implications
            - Easements and rights of way
            - Boundary disputes or uncertainties
            - Planning permissions and breaches
            - Building regulation compliance
            - Probate or power of attorney concerns
            - Current tenancies and their terms

            3. PHYSICAL PROPERTY RISKS
            Detail any evidence of:
            - Non-standard construction elements
            - Structural issues or subsidence
            - Mining activity and ground stability
            - Electricity pylons/power lines (with distances and implications)
            - Japanese knotweed
            - Environmental hazards
            - Flooding risks
            - Contamination

            4. DEVELOPMENT AND USAGE RESTRICTIONS
            Analyze implications for:
            - HMO conversion potential
            - Renovation restrictions
            - Change of use limitations
            - Future development constraints
            - Local authority restrictions

            5. FINANCIAL AND MORTGAGE CONSIDERATIONS
            - Impacts on mortgage availability
            - Remortgage restrictions
            - Valuation impacts
            - Insurance implications
            - Service charges or ground rent

            6. NEARBY DEVELOPMENTS AND EXTERNAL FACTORS
            - Planned developments that could affect value
            - Infrastructure projects
            - Neighboring property issues
            - Local authority proposals

            For each identified risk or issue, provide:
            - Detailed description of the issue
            - Potential impact on purchase/ownership
            - Required mitigation steps
            - Impact on future saleability/rentability/mortgageability
            - Estimated costs for resolution (if applicable)
            - Whether further professional investigation is needed

            If any critical information is missing from the legal pack or requires verification, explicitly state what needs to be checked and why it's important.

            Here are the documents to analyze:
            {'\n'.join(all_content)}"""

            completion = client.messages.create(
                system="You are a conveyancer analyzing legal packs for auction properties.",
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            analysis = completion.content

            # Save analysis if we have a property ID
            if property_id:
                analysis_record = DocumentAnalysis(
                    property_id=property_id,
                    anthropic_response=analysis,
                    identified_risks="",  # Could parse this from the analysis if needed
                    confidence_score=0.0  # Could be calculated based on certainty markers in the text
                )
                db.session.add(analysis_record)
                db.session.commit()

            return jsonify({
                'analysis': analysis,
                'property_id': property_id
            })

        finally:
            document_service._quit_driver()

    except Exception as e:
        logger.error(f"Error analyzing legal pack: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5005)
