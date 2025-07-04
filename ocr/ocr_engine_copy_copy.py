import cv2
import numpy as np
import pytesseract
import re

def extract_voter_data(image_array):
    """
    Extract voter data from numpy image array
    Returns: full_text, voter_id, age, house_number
    """
    # Validate input
    if not isinstance(image_array, np.ndarray) or len(image_array.shape) not in (2, 3):
        raise ValueError("Invalid image array format")
    
    # Preprocess entire image first
    processed_img = preprocess_image(image_array)
    h, w = processed_img.shape[:2]
    
    # Extract ROIs using precise coordinates
    voter_id_roi = extract_roi(processed_img, 0.6, 0.04, 0.98, 0.18, h, w)
    age_roi = extract_roi(processed_img, 0.12, 0.58, 0.17, 0.7, h, w)
    house_roi = extract_roi(processed_img, 0.226, 0.47, 0.5, 0.59, h, w)
    
    # Perform OCR on full image
    full_text = pytesseract.image_to_string(processed_img, lang='hin+eng', config='--oem 3 --psm 6').strip()
    
    # Extract individual fields
    voter_id = extract_voter_id(voter_id_roi)
    age = extract_age(age_roi)
    house_number = extract_house_number(house_roi)
    
    # Fallback if ROI extraction failed
    if not age:
        age = extract_age_from_text(full_text)
    if not house_number:
        house_number = extract_house_from_text(full_text)
    
    return full_text, voter_id, age, house_number

def extract_roi(img, x1_ratio, y1_ratio, x2_ratio, y2_ratio, h, w):
    """Extract region of interest from image"""
    x1 = int(x1_ratio * w)
    y1 = int(y1_ratio * h)
    x2 = int(x2_ratio * w)
    y2 = int(y2_ratio * h)
    return img[y1:y2, x1:x2]

def preprocess_image(img):
    """Enhanced image preprocessing pipeline"""
    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    
    # Denoising
    denoised = cv2.fastNlMeansDenoising(gray, h=12, templateWindowSize=7, searchWindowSize=21)
    
    # Contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # Binarization with special handling for thin characters
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Morphological operations to enhance text
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    return processed

def extract_voter_id(roi):
    """Extract voter ID with optimized preprocessing"""
    # Special preprocessing for ID field
    processed = cv2.resize(roi, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # OCR with whitelist
    config = '--oem 3 --psm 8 '
    text = pytesseract.image_to_string(thresh, config=config).strip()
    
    # Clean and return
    return text

def extract_age(roi):
    """Extract age with special handling for digit '1'"""
    # Enhanced preprocessing for digits
    processed = preprocess_for_digits(roi)
    
    # Multiple OCR attempts with different configurations
    configs = [
        '--oem 3 --psm 10 tessedit_char_whitelist=0123456789',  # Single character
        '--oem 3 --psm 8 tessedit_char_whitelist=0123456789',   # Word
        '--oem 1 --psm 10 tessedit_char_whitelist=0123456789',   # Different engine
    ]
    
    candidates = []
    for config in configs:
        text = pytesseract.image_to_string(processed, config=config).strip()
        digits = re.sub(r'\D', '', text)  # Remove non-digit characters
        if validate_age(digits):
            candidates.append(digits)
    
    # Return most common valid result
    if candidates:
        return max(set(candidates), key=candidates.count)
    return ""

def preprocess_for_digits(roi):
    """Special preprocessing for digit recognition"""
    # Resize to make digits clearer
    resized = cv2.resize(roi, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    
    # Thresholding optimized for digits
    _, binary = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Morphological operations to enhance digits
    kernel = np.ones((2, 2), np.uint8)
    dilated = cv2.dilate(binary, kernel, iterations=1)
    
    # Add padding around digits
    padded = cv2.copyMakeBorder(dilated, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=0)
    
    return padded

def validate_age(age_str):
    """Validate age format and range"""
    if not age_str or not age_str.isdigit():
        return False
    age = int(age_str)
    return 18 <= age <= 120

def extract_house_number(roi):
    """Extract house number with Hindi support"""
    # Multiple preprocessing variants
    variants = [
        preprocess_for_hindi(roi, binarize=True),
        preprocess_for_hindi(roi, binarize=False),
        cv2.bitwise_not(preprocess_for_hindi(roi, binarize=True))
    ]
    
    texts = []
    for variant in variants:
        text = pytesseract.image_to_string(variant, lang='hin+eng', config='--oem 3 --psm 6').strip()
        if text:
            texts.append(text)
    
    if texts:
        # Clean while preserving Hindi characters
        cleaned = re.sub(r'[^\w\s\u0900-\u097F]', '', max(texts, key=len))
        return cleaned.strip()
    return ""

def preprocess_for_hindi(roi, binarize=True):
    """Preprocessing optimized for Hindi text"""
    # Resize for better recognition
    resized = cv2.resize(roi, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
    
    if binarize:
        # Adaptive thresholding
        return cv2.adaptiveThreshold(resized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 51, 12)
    else:
        # Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        return clahe.apply(resized)

def extract_age_from_text(text):
    """Fallback: extract age from full text"""
    patterns = [
        r'आयु\s*[:：]\s*(\d+)',
        r'Age\s*[:：]\s*(\d+)',
        r'(\b\d{2}\b)(?=\s*वर्ष)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            age = match.group(1)
            if validate_age(age):
                return age
    return ""

def extract_house_from_text(text):
    """Fallback: extract house number from full text"""
    patterns = [
        r'मकान\s*संख्या\s*[:：]\s*([^\n]+?)(?=\s*(?:आयु|लिंग|Age|Gender|$))',
        r'House\s*No\.?\s*[:：]\s*([^\n]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""