import os
import zipfile
import tempfile
import logging
import json
from datetime import datetime
from app import process_zip_file, process_document
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_zip():
    """Create a test zip file from the Lot_62_DocumentArchive directory"""
    source_dir = os.path.join(os.path.dirname(__file__), 'Lot_62_DocumentArchive (1)')
    zip_path = os.path.join(os.path.dirname(__file__), 'test_lot_62.zip')
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                if not file.startswith('~'):  # Skip temp files
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    logger.info(f"Adding {arcname} to zip")
                    zipf.write(file_path, arcname)
    
    return zip_path

def save_processing_results(documents):
    """Save processing results to a JSON file"""
    results = {
        "documents": [],
        "initial_analysis": "",  # This would be filled by your analysis function
        "processed_at": datetime.now().isoformat(),
        "total_documents": len(documents)
    }
    
    for doc in documents:
        doc_info = {
            "name": doc["name"],
            "content": f"\n{'='*50}\nDOCUMENT: {doc['name']}\n{'='*50}\n{doc.get('content', '')}",
            "length": doc.get('length', 0)
        }
        results["documents"].append(doc_info)
    
    # Save to a file in document_storage with a unique name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_processing_results_{timestamp}.json"
    filepath = os.path.join(os.path.dirname(__file__), 'document_storage', filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to {filepath}")
    return filepath

def test_process_documents():
    """Test processing each document individually"""
    source_dir = os.path.join(os.path.dirname(__file__), 'Lot_62_DocumentArchive (1)')
    processed_docs = []
    
    logger.info("\nTesting individual document processing:")
    logger.info("=" * 50)
    
    for file in sorted(os.listdir(source_dir)):
        if file.startswith('~'):
            continue
            
        file_path = os.path.join(source_dir, file)
        logger.info(f"\nProcessing: {file}")
        
        try:
            content = process_document(file_path)
            if content and content.strip():
                logger.info(f"Success - Extracted {len(content)} characters")
                processed_docs.append({
                    "name": file,
                    "content": content,
                    "length": len(content)
                })
            else:
                logger.error(f"Failed - No content extracted")
        except Exception as e:
            logger.error(f"Error processing {file}: {str(e)}")
    
    # Save results to JSON
    results_file = save_processing_results(processed_docs)
    logger.info(f"Individual processing results saved to {results_file}")

def test_zip_processing():
    """Test processing the entire zip file"""
    zip_path = create_test_zip()
    
    try:
        logger.info("\nTesting zip file processing:")
        logger.info("=" * 50)
        
        processed_files, failed_files, summary = process_zip_file(zip_path)
        
        logger.info("\nProcessed Files:")
        for file in processed_files:
            logger.info(f"✓ {file['name']} ({file['length']} characters)")
            
        logger.info("\nFailed Files:")
        for file in failed_files:
            logger.info(f"✗ {file}")
            
        logger.info("\nProcessing Summary:")
        logger.info(summary)
        
        # Save zip processing results
        results_file = save_processing_results(processed_files)
        logger.info(f"Zip processing results saved to {results_file}")
        
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

if __name__ == "__main__":
    logger.info("Starting document processing tests")
    test_process_documents()
    test_zip_processing()
