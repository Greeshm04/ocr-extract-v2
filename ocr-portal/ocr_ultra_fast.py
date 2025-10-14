# -- coding: utf-8 --
"""
ULTRA-FAST Router OCR - Single pass, maximum speed
Target: < 10 seconds per image with high accuracy
"""

import cv2
import numpy as np
import os
import re
import time
import logging
import easyocr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UltraFastRouterOCR:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UltraFastRouterOCR, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        logger.info("🚀 Initializing Ultra-Fast Router OCR...")
        
        # Initialize ONLY EasyOCR (fastest and most accurate for English)
        self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        logger.info("✅ EasyOCR Ready")
        
        # Optimized regex patterns
        self.patterns = {
            'wpa_key': r'(?:WPA[:\s]*|Key[:\s]*|Password[:\s]*)([A-Za-z0-9]{8,64})',
            'ssid': r'(?:SSID[:\s]*|Network[:\s]*)([A-Za-z0-9_-]{3,32})',
            'ip_address': r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b',
            'mac_address': r'\b([0-9A-Fa-f]{2}[:-]?){5}[0-9A-Fa-f]{2}\b',
            'model_number': r'(?:Model[:\s]*|P/N[:\s]*|Part[:\s]*)([A-Z0-9-]{4,20})',
            'serial_number': r'(?:S/N[:\s]*|Serial[:\s]*)([A-Z0-9]{8,20})',
            'username': r'(?:User(?:name)?[:\s]*)([A-Za-z0-9_-]{3,20})',
            'password': r'(?:Pass(?:word)?[:\s]*)([A-Za-z0-9]{4,20})',
        }
        
        self._initialized = True
    
    def preprocess_fast(self, image):
        """Single best preprocessing method"""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # OTSU threshold - best for router labels
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def extract_text(self, image):
        """Single-pass OCR extraction"""
        try:
            # EasyOCR with optimized settings
            results = self.reader.readtext(
                image,
                detail=0,  # No bounding boxes (faster)
                paragraph=False,  # Line by line (faster)
                batch_size=1  # Process one at a time (lower memory)
            )
            return ' '.join(results)
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return ""
    
    def extract_field(self, text, field_name):
        """Extract specific field using regex"""
        if field_name not in self.patterns:
            return None
        
        pattern = self.patterns[field_name]
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        if matches:
            # Return first match (usually the correct one)
            match = matches[0]
            if isinstance(match, tuple):
                match = ''.join(match)
            
            # Clean up
            match = match.strip()
            
            # Validate based on field type
            if field_name == 'ip_address':
                # Validate IP
                parts = match.split('.')
                if len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts if p.isdigit()):
                    return match
            elif field_name == 'mac_address':
                # Clean MAC
                return match.replace('-', ':').lower()
            else:
                return match
        
        return None
    
    def process_image_ultra_fast(self, image_path):
        """Ultra-fast single-pass processing"""
        start_time = time.time()
        
        logger.info(f"🔍 Processing: {os.path.basename(image_path)}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"❌ Could not load: {image_path}")
            return {}
        
        # Single preprocessing
        processed = self.preprocess_fast(image)
        
        # Single OCR pass
        text = self.extract_text(processed)
        
        logger.info(f"   📝 Extracted text ({len(text)} chars)")
        
        # Extract all fields
        result = {}
        for field_name in self.patterns.keys():
            value = self.extract_field(text, field_name)
            if value:
                result[field_name] = value
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Completed in {elapsed:.2f}s")
        logger.info(f"   📊 Found {len(result)} fields: {', '.join(result.keys())}")
        
        return result


def process_single_image_ultra_fast(image_path):
    """
    Ultra-fast processing entry point
    Target: < 10 seconds per image
    """
    logger.info(f"🚀 Ultra-Fast OCR: {image_path}")
    
    ocr = UltraFastRouterOCR()
    result = ocr.process_image_ultra_fast(image_path)
    
    # Always return a dict (even if empty)
    return result if result else {}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
        if os.path.exists(test_image):
            result = process_single_image_ultra_fast(test_image)
            print("\n" + "="*60)
            print("📊 EXTRACTED INFORMATION")
            print("="*60)
            for key, value in result.items():
                print(f"  • {key}: {value}")
            print("="*60)
        else:
            print(f"❌ Image not found: {test_image}")
    else:
        print("Usage: python ocr_ultra_fast.py <image_path>")

