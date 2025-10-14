# -- coding: utf-8 --
"""
Fast OCR Processing for Router Labels
Optimized version with PIL compatibility fix and reduced processing time
"""

import cv2
import numpy as np
import os
from PIL import Image
import pytesseract
import easyocr
import re
import warnings
warnings.filterwarnings('ignore')

# Fix for PIL.Image.ANTIALIAS deprecation in Pillow 10+
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS
    print("✅ Fixed PIL.Image.ANTIALIAS compatibility")

class FastRouterInfoExtractor:
    _instance = None
    _reader = None
    
    def __new__(cls):
        """Singleton pattern to avoid reinitializing EasyOCR reader"""
        if cls._instance is None:
            cls._instance = super(FastRouterInfoExtractor, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if FastRouterInfoExtractor._reader is not None:
            # Already initialized
            return
            
        print("🚀 Initializing Fast OCR engines...")
        
        # Initialize EasyOCR once (singleton pattern for speed)
        FastRouterInfoExtractor._reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        
        # Check if Tesseract is available
        self.tesseract_available = False
        try:
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            print("✅ Tesseract OCR: Available")
        except:
            print("⚠  Tesseract OCR: Not available (using EasyOCR only)")
        
        print("✅ EasyOCR: Ready (singleton)")

        # Define patterns for common router information
        self.patterns = {
            'wpa_key': [
                r'WPA\s*Key\s*:?\s*([A-Za-z0-9]+)',
                r'Key\s*:?\s*([A-Za-z0-9]{8,})',
                r'WPA\s*:?\s*([A-Za-z0-9]{8,})',
            ],
            'ip_address': [
                r'IP\s*Address\s*:?\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
                r'IP\s*:?\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
                r'(192\.168\.\d{1,3}\.\d{1,3})',
                r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
            ],
            'ssid': [
                r'SSID\s*:?\s*([A-Za-z0-9_-]+)',
                r'Network\s*Name\s*:?\s*([A-Za-z0-9_-]+)',
                r'WiFi\s*Name\s*:?\s*([A-Za-z0-9_-]+)',
            ],
            'mac_address': [
                r'MAC\s*:?\s*([A-Fa-f0-9]{2}[:-]?[A-Fa-f0-9]{2}[:-]?[A-Fa-f0-9]{2}[:-]?[A-Fa-f0-9]{2}[:-]?[A-Fa-f0-9]{2}[:-]?[A-Fa-f0-9]{2})',
                r'([A-Fa-f0-9]{12})',
                r'MTA\s*MAC\s*:?\s*([A-Fa-f0-9]+)',
            ],
            'model_number': [
                r'Model\s*:?\s*([A-Za-z0-9-_]+)',
                r'Model\s*No\s*:?\s*([A-Za-z0-9-_]+)',
                r'GigaSpire\s*BLAST\s*Model\s*:?\s*([A-Za-z0-9-_]+)',
            ],
            'serial_number': [
                r'Serial\s*No\s*:?\s*([A-Za-z0-9]+)',
                r'S/N\s*:?\s*([A-Za-z0-9]+)',
                r'Serial\s*:?\s*([A-Za-z0-9]+)',
            ]
        }
        print("✅ Fast RouterInfoExtractor initialized!")

    def preprocess_image_fast(self, image):
        """Fast preprocessing with only the most effective methods"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        processed_images = {}

        # Method 1: Enhanced contrast (most effective)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        processed_images['enhanced'] = enhanced

        # Method 2: OTSU threshold (fast and effective)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images['otsu'] = thresh

        return processed_images

    def extract_text_easyocr(self, image):
        """Extract text using EasyOCR"""
        try:
            results = FastRouterInfoExtractor._reader.readtext(image, detail=0, paragraph=False)
            return ' '.join(results)
        except Exception as e:
            print(f"EasyOCR error: {e}")
            return ""

    def extract_text_tesseract(self, image, config='--psm 6'):
        """Extract text using Tesseract OCR"""
        try:
            text = pytesseract.image_to_string(image, config=config)
            return text.strip()
        except Exception as e:
            print(f"Tesseract error: {e}")
            return ""

    def extract_username_password(self, text):
        """Extract username/password pairs"""
        username = None
        password = None

        token = r'[A-Za-z0-9._-]{2,64}'

        patterns = [
            rf'(?i)\buser(?:name)?\s*[:;\-–—]?\s*({token})\s*(?:[,;|\-–—\s]{{1,6}})\s*pass(?:word)?\s*[:;\-–—]?\s*({token})\b',
            rf'(?i)\buser\s*/\s*password\s*[:;]?\s*({token})\s*/\s*({token})\b',
            rf'(?i)\busername?\s*[:;]?\s*({token})\D{{0,8}}?password?\s*[:;]?\s*({token})',
        ]

        def is_ip(s):
            return re.fullmatch(r'\d{1,3}(?:\.\d{1,3}){3}', s) is not None

        def is_mac(s):
            return re.fullmatch(r'(?:[A-Fa-f0-9]{2}[:\-]?){5}[A-Fa-f0-9]{2}', s) is not None or re.fullmatch(r'[A-Fa-f0-9]{12}', s) is not None

        def clean_token(t):
            if t is None:
                return None
            return t.strip(" \t\n\r:;,.\"'`[]()<>")

        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if not m:
                continue
            u = clean_token(m.group(1))
            p = clean_token(m.group(2))

            if not u or not p:
                continue
            if is_ip(u) or is_ip(p) or is_mac(u) or is_mac(p):
                continue

            username, password = u, p
            return username, password

        return None, None

    def extract_information(self, text):
        """Extract specific information using regex patterns"""
        extracted_info = {}

        # Clean up text
        text = re.sub(r'\s+', ' ', text)

        # Extract username and password
        username, password = self.extract_username_password(text)
        extracted_info['username'] = username
        extracted_info['password'] = password

        # Extract other fields
        for info_type, patterns in self.patterns.items():
            if info_type not in extracted_info:
                extracted_info[info_type] = None

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_info[info_type] = match.group(1)
                    break

        return extracted_info

    def process_image_fast(self, image_path, verbose=False):
        """Fast processing with optimized pipeline"""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ Could not load image: {image_path}")
            return None

        if verbose:
            print(f"📸 Processing: {os.path.basename(image_path)}")

        # Fast preprocessing (only 2 methods instead of 5)
        processed_images = self.preprocess_image_fast(image)

        results = {}

        # Use hybrid approach: EasyOCR for main extraction, Tesseract as backup
        for preprocess_name, proc_image in processed_images.items():
            # Try EasyOCR first (usually more accurate for printed text)
            text_easy = self.extract_text_easyocr(proc_image)
            
            # Also try Tesseract if available (combine results)
            text_tess = ""
            if self.tesseract_available:
                text_tess = self.extract_text_tesseract(proc_image, '--psm 6')
            
            # Combine both texts for better coverage
            combined_text = text_easy + " " + text_tess
            
            extracted_info = self.extract_information(combined_text)
            
            results[preprocess_name] = {
                'text': combined_text,
                'extracted_info': extracted_info
            }

            if verbose:
                print(f"✅ {preprocess_name}: {len(combined_text)} chars extracted")

        return results

    def combine_results_fast(self, results):
        """Fast result combination"""
        final_info = {}

        # Initialize with empty values
        all_fields = list(self.patterns.keys()) + ['username', 'password']
        for info_type in all_fields:
            final_info[info_type] = None

        # Priority: enhanced > otsu
        priority_order = ['enhanced', 'otsu']

        for info_type in final_info.keys():
            for preprocess in priority_order:
                try:
                    if preprocess in results:
                        value = results[preprocess]['extracted_info'].get(info_type)
                        if value and not final_info[info_type]:
                            final_info[info_type] = value
                            break
                except:
                    continue

        return final_info


def process_single_image_fast(image_path, output_format='dict'):
    """
    Fast processing for a single router image
    
    Args:
        image_path: Path to the image file
        output_format: 'dict' or 'print'
    
    Returns:
        Dictionary with extracted information
    """
    print(f"   [OCR] Processing: {image_path}")
    
    extractor = FastRouterInfoExtractor()
    print(f"   [OCR] Extractor initialized")
    
    results = extractor.process_image_fast(image_path, verbose=True)

    if not results:
        print("   [OCR] ❌ Failed to process image - results is None/empty")
        # Return empty dict instead of None
        return {
            'wpa_key': None,
            'ip_address': None,
            'ssid': None,
            'mac_address': None,
            'model_number': None,
            'serial_number': None,
            'username': None,
            'password': None
        }

    print(f"   [OCR] Got {len(results)} preprocessing results")
    final_info = extractor.combine_results_fast(results)
    print(f"   [OCR] Combined into final result")

    if output_format == 'print':
        print("\n" + "="*50)
        print("📊 EXTRACTED INFORMATION")
        print("="*50)
        for key, value in final_info.items():
            icon = "✅" if value else "❌"
            display_name = key.replace('_', ' ').title()
            print(f"{icon} {display_name}: {value if value else 'Not found'}")
        print("="*50)

    return final_info


print("🚀 Fast Router OCR Extractor Loaded!")
print("="*60)

