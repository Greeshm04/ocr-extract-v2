# -- coding: utf-8 --
"""
World-Class Router OCR System - FAST & ACCURATE
⚡ OPTIMIZED FOR SPEED:
  - Only 3 preprocessing methods (was 8) = 3x faster
  - Only 2 OCR engines per image (EasyOCR + PaddleOCR, skip slow Tesseract) = 2x faster
  - Total: 6x FASTER than previous version
  
🎯 ACCURACY:
  - Multi-engine voting system
  - Advanced pattern matching with validation
  - Smart field extraction
"""

import cv2
import numpy as np
import os
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import easyocr
import re
import time
import warnings
from typing import Dict, List, Tuple, Optional
import logging

# Advanced libraries for better OCR
try:
    import paddleocr
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    print("⚠️  PaddleOCR not available - install with: pip install paddlepaddle paddleocr")

try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    TROCR_AVAILABLE = True
except ImportError:
    TROCR_AVAILABLE = False
    print("ℹ️  TrOCR not available - install with: pip install transformers")

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix PIL compatibility
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

class WorldClassRouterOCR:
    """
    Multi-engine OCR system with advanced preprocessing and validation
    """
    
    def __init__(self):
        logger.info("🚀 Initializing World-Class Router OCR...")
        
        # Initialize engines (singleton pattern)
        self._init_engines()
        
        # Advanced regex patterns with validation
        self._init_patterns()
        
        # Field validation rules
        self._init_validators()
        
        logger.info("✅ World-Class OCR initialized with all engines!")
    
    def _init_engines(self):
        """Initialize all available OCR engines"""
        self.engines = {}
        
        # EasyOCR (fast, good for printed text)
        try:
            self.engines['easyocr'] = easyocr.Reader(['en'], gpu=False, verbose=False)
            logger.info("✅ EasyOCR: Ready")
        except Exception as e:
            logger.warning(f"⚠️  EasyOCR failed: {e}")
        
        # PaddleOCR (excellent for Chinese/English, very accurate)
        if PADDLE_AVAILABLE:
            try:
                self.engines['paddle'] = paddleocr.PaddleOCR(use_angle_cls=True, lang='en')
                logger.info("✅ PaddleOCR: Ready")
            except Exception as e:
                logger.warning(f"⚠️  PaddleOCR failed: {e}")
        
        # Tesseract (configurable, good for structured text)
        try:
            pytesseract.get_tesseract_version()
            logger.info("✅ Tesseract: Ready")
        except Exception as e:
            logger.warning(f"⚠️  Tesseract failed: {e}")
    
    def _init_patterns(self):
        """Advanced regex patterns with field-specific validation"""
        self.patterns = {
            'wpa_key': [
                r'(?:WPA\s*Key?|Key)\s*:?\s*([A-Fa-f0-9]{8,})',
                r'([A-Fa-f0-9]{8,32})',  # General hex pattern
            ],
            'ip_address': [
                r'(?:IP\s*Address?|IP)\s*:?\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
                r'(192\.168\.\d{1,3}\.\d{1,3})',
                r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
            ],
            'ssid': [
                r'(?:SSID|Network\s*Name)\s*:?\s*([A-Za-z0-9_-]{4,})',
                r'([A-Za-z0-9_-]{4,32})',
            ],
            'mac_address': [
                r'(?:MAC|MAC\s*Address)\s*:?\s*([A-Fa-f0-9]{2}[:-]?[A-Fa-f0-9]{2}[:-]?[A-Fa-f0-9]{2}[:-]?[A-Fa-f0-9]{2}[:-]?[A-Fa-f0-9]{2}[:-]?[A-Fa-f0-9]{2})',
                r'([A-Fa-f0-9]{12})',
            ],
            'mta_mac': [
                r'(?:MTA\s*MAC)\s*:?\s*([A-Fa-f0-9]{12})',
            ],
            'model_number': [
                r'(?:Model\s*No\.?|Model\s*Number)\s*:?\s*([A-Za-z0-9\-\.\s]+)',
                r'(\d{3}-\d{5}\s*\d{2})',  # Pattern like "100-05921 10"
            ],
            'serial_number': [
                r'(?:Serial\s*No\.?|Serial\s*Number|S\/N)\s*:?\s*([A-Za-z0-9]+)',
                r'(\d{12})',  # 12-digit serial
            ],
            'username': [
                r'(?:User|Username)\s*:?\s*([A-Za-z0-9_]+)',
            ],
            'password': [
                r'(?:Pass|Password)\s*:?\s*([A-Za-z0-9]+)',
            ]
        }
    
    def _init_validators(self):
        """Field validation rules"""
        self.validators = {
            'wpa_key': lambda x: len(x) >= 8 and all(c in '0123456789ABCDEFabcdef' for c in x),
            'ip_address': lambda x: self._is_valid_ip(x),
            'ssid': lambda x: 4 <= len(x) <= 32 and all(c.isalnum() or c in '_-' for c in x),
            'mac_address': lambda x: len(x) in [12, 17] and self._is_valid_mac(x),
            'mta_mac': lambda x: len(x) in [12, 17] and self._is_valid_mac(x),
            'model_number': lambda x: len(x) >= 3,
            'serial_number': lambda x: len(x) >= 6 and x.isalnum(),
            'username': lambda x: len(x) >= 2 and x.isalnum(),
            'password': lambda x: len(x) >= 4 and x.isalnum(),
        }
    
    def _is_valid_ip(self, ip):
        """Validate IP address"""
        try:
            parts = ip.split('.')
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except:
            return False
    
    def _is_valid_mac(self, mac):
        """Validate MAC address"""
        mac = mac.replace(':', '').replace('-', '')
        return len(mac) == 12 and all(c in '0123456789ABCDEFabcdef' for c in mac)
    
    def preprocess_image_advanced(self, image):
        """
        FAST preprocessing with only the TOP 3 most effective techniques
        Reduced from 8 methods to 3 for 3x speed improvement
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        processed = {}
        
        # 1. Original - works best for clear images
        processed['original'] = gray
        
        # 2. OTSU threshold - best for router labels (high contrast text)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed['otsu'] = otsu
        
        # 3. CLAHE - best for low contrast or uneven lighting
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        processed['clahe'] = enhanced
        
        return processed
    
    def extract_text_easyocr(self, image):
        """Extract text using EasyOCR"""
        try:
            results = self.engines['easyocr'].readtext(image, detail=0, paragraph=False)
            return ' '.join(results)
        except Exception as e:
            logger.warning(f"EasyOCR error: {e}")
            return ""
    
    def extract_text_paddleocr(self, image):
        """Extract text using PaddleOCR"""
        if 'paddle' not in self.engines:
            return ""
        try:
            # PaddleOCR.ocr() doesn't accept 'cls' parameter, it uses use_angle_cls from initialization
            results = self.engines['paddle'].ocr(image)
            if results and results[0]:
                text_parts = []
                for line in results[0]:
                    if line and len(line) >= 2:
                        text_parts.append(line[1][0])
                return ' '.join(text_parts)
            return ""
        except Exception as e:
            logger.warning(f"PaddleOCR error: {e}")
            return ""
    
    def extract_text_tesseract(self, image, configs=None):
        """Extract text using Tesseract with multiple configurations"""
        if configs is None:
            configs = [
                '--psm 6',  # Uniform block of text
                '--psm 4',  # Single column text
                '--psm 8',  # Single word
                '--psm 13', # Raw line
                '--psm 11', # Sparse text
            ]
        
        best_text = ""
        for config in configs:
            try:
                text = pytesseract.image_to_string(image, config=config).strip()
                if len(text) > len(best_text):
                    best_text = text
            except Exception as e:
                logger.warning(f"Tesseract error with {config}: {e}")
        
        return best_text
    
    def extract_text_all_engines(self, image):
        """
        FAST: Use only the TOP 2 most accurate and fastest engines
        EasyOCR + PaddleOCR (skip Tesseract for speed)
        """
        all_texts = []
        
        # EasyOCR - FAST and accurate for English
        if 'easyocr' in self.engines:
            text = self.extract_text_easyocr(image)
            if text:
                all_texts.append(('easyocr', text))
        
        # PaddleOCR - Very accurate, good complement to EasyOCR
        if 'paddle' in self.engines:
            text = self.extract_text_paddleocr(image)
            if text:
                all_texts.append(('paddle', text))
        
        # Tesseract DISABLED for speed (slowest engine)
        # Can enable if accuracy is more important than speed
        
        return all_texts
    
    def extract_field_advanced(self, text, field_name):
        """
        Advanced field extraction with validation and confidence scoring
        """
        if field_name not in self.patterns:
            return None
        
        candidates = []
        
        for pattern in self.patterns[field_name]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match.group(1).strip()
                
                # Clean up the value
                value = self._clean_value(value, field_name)
                
                # Validate
                if self._validate_field(field_name, value):
                    confidence = self._calculate_confidence(match, text, field_name)
                    candidates.append((value, confidence))
        
        # Return highest confidence candidate
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
    
    def _clean_value(self, value, field_name):
        """Clean and normalize field values"""
        # Remove common OCR artifacts
        value = re.sub(r'[^\w\.\-:]', '', value)
        
        # Field-specific cleaning
        if field_name in ['mac_address', 'mta_mac']:
            # Remove separators and normalize
            value = value.replace(':', '').replace('-', '').upper()
        elif field_name == 'ip_address':
            # Ensure valid IP format
            value = value.replace(' ', '')
        elif field_name in ['wpa_key', 'serial_number']:
            # Remove spaces
            value = value.replace(' ', '')
        
        return value
    
    def _validate_field(self, field_name, value):
        """Validate field value"""
        if not value or field_name not in self.validators:
            return False
        
        return self.validators[field_name](value)
    
    def _calculate_confidence(self, match, text, field_name):
        """Calculate confidence score for a match"""
        confidence = 0.5  # Base confidence
        
        # Length bonus
        if field_name in ['serial_number'] and len(match.group(1)) >= 10:
            confidence += 0.2
        elif field_name in ['wpa_key'] and len(match.group(1)) >= 12:
            confidence += 0.3
        
        # Position bonus (earlier in text is usually better)
        position_ratio = match.start() / len(text)
        confidence += (1 - position_ratio) * 0.1
        
        # Pattern specificity bonus
        if ':' in match.group(0):  # Labeled fields are more reliable
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def extract_credentials_advanced(self, text):
        """
        Advanced username/password extraction
        """
        # Multiple patterns for credential extraction
        patterns = [
            # admin/82fe6124
            r'([a-zA-Z0-9_]+)/([a-zA-Z0-9]+)',
            # User: admin Password: 82fe6124
            r'(?:User|Username)\s*:?\s*([a-zA-Z0-9_]+).*?(?:Pass|Password)\s*:?\s*([a-zA-Z0-9]+)',
            # admin 82fe6124 (space separated)
            r'([a-zA-Z0-9_]+)\s+([a-zA-Z0-9]{6,})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                username = match.group(1).strip()
                password = match.group(2).strip()
                
                # Validate
                if len(username) >= 2 and len(password) >= 4:
                    return username, password
        
        return None, None
    
    def process_image_world_class(self, image_path, verbose=False):
        """
        World-class OCR processing with all engines and techniques
        """
        start_time = time.time()
        
        if verbose:
            logger.info(f"🔍 Processing: {os.path.basename(image_path)}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"❌ Could not load image: {image_path}")
            return None
        
        # Advanced preprocessing
        if verbose:
            logger.info("   📐 Advanced preprocessing...")
        processed_images = self.preprocess_image_advanced(image)
        
        # Extract text from all engines and preprocessing combinations
        all_results = {}
        
        for preprocess_name, proc_image in processed_images.items():
            if verbose:
                logger.info(f"   🔍 Processing {preprocess_name}...")
            
            # Get text from all engines
            engine_texts = self.extract_text_all_engines(proc_image)
            
            # Combine all engine results
            combined_text = ' '.join([text for _, text in engine_texts])
            
            # Extract fields
            extracted_info = {}
            
            # Extract standard fields
            for field_name in self.patterns.keys():
                if field_name not in ['username', 'password']:
                    extracted_info[field_name] = self.extract_field_advanced(combined_text, field_name)
            
            # Extract credentials
            username, password = self.extract_credentials_advanced(combined_text)
            extracted_info['username'] = username
            extracted_info['password'] = password
            
            all_results[preprocess_name] = {
                'text': combined_text,
                'engines': engine_texts,
                'extracted_info': extracted_info
            }
        
        # Combine results using voting system
        final_info = self._combine_results_voting(all_results)
        
        elapsed = time.time() - start_time
        if verbose:
            logger.info(f"✅ Processing completed in {elapsed:.2f}s")
            found_fields = [k for k, v in final_info.items() if v is not None]
            logger.info(f"   📊 Extracted {len(found_fields)} fields: {', '.join(found_fields)}")
        
        return final_info
    
    def _combine_results_voting(self, all_results):
        """
        Combine results from all preprocessing methods using voting system
        """
        final_info = {}
        
        # Initialize all fields
        all_fields = list(self.patterns.keys()) + ['username', 'password']
        for field in all_fields:
            final_info[field] = None
        
        # Voting system: each preprocessing method gets a vote
        field_votes = {}
        for field in all_fields:
            field_votes[field] = {}
        
        # Collect votes from all preprocessing methods
        for preprocess_name, result in all_results.items():
            for field, value in result['extracted_info'].items():
                if value is not None:
                    if value not in field_votes[field]:
                        field_votes[field][value] = []
                    field_votes[field][value].append(preprocess_name)
        
        # Select winner for each field (most votes)
        for field, votes in field_votes.items():
            if votes:
                # Sort by number of votes
                sorted_votes = sorted(votes.items(), key=lambda x: len(x[1]), reverse=True)
                winner_value = sorted_votes[0][0]
                winner_count = len(sorted_votes[0][1])
                
                # Only accept if at least 2 votes or high confidence
                if winner_count >= 2 or self._is_high_confidence(winner_value, field):
                    final_info[field] = winner_value
        
        return final_info
    
    def _is_high_confidence(self, value, field):
        """Check if value has high confidence based on patterns"""
        if field == 'ip_address' and re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', value):
            return True
        elif field == 'mac_address' and len(value) == 12 and all(c in '0123456789ABCDEFabcdef' for c in value):
            return True
        elif field == 'serial_number' and len(value) >= 10 and value.isdigit():
            return True
        elif field == 'wpa_key' and len(value) >= 12 and all(c in '0123456789ABCDEFabcdef' for c in value):
            return True
        
        return False


def process_single_image_world_class(image_path, output_format='dict'):
    """
    World-class processing for a single router image
    
    Args:
        image_path: Path to the image file
        output_format: 'dict' or 'print'
    
    Returns:
        Dictionary with extracted information
    """
    logger.info(f"🚀 Starting world-class OCR processing: {image_path}")
    
    extractor = WorldClassRouterOCR()
    final_info = extractor.process_image_world_class(image_path, verbose=True)
    
    if output_format == 'print':
        print("\n" + "="*60)
        print("📊 WORLD-CLASS EXTRACTED INFORMATION")
        print("="*60)
        for key, value in final_info.items():
            icon = "✅" if value else "❌"
            display_name = key.replace('_', ' ').title()
            print(f"{icon} {display_name}: {value if value else 'Not found'}")
        print("="*60)
    
    return final_info


if __name__ == "__main__":
    logger.info("🚀 World-Class Router OCR System")
    logger.info("="*60)
    
    # Test with a sample image
    import sys
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
        if os.path.exists(test_image):
            result = process_single_image_world_class(test_image, output_format='print')
        else:
            logger.error(f"Image not found: {test_image}")
    else:
        logger.info("Usage: python ocr_world_class.py <image_path>")
