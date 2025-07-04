import pytesseract
from config import TESSERACT_PATH
import cv2
import numpy as np
import os
import time
import re
from PIL import Image, ImageEnhance

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def perform_ocr(image):
    os.makedirs("crops", exist_ok=True)
    h, w = image.shape[:2]
    
    # OCR for the full image
    config_hindi = '--oem 1 --psm 6'
    full_text = pytesseract.image_to_string(image, lang='hin+eng', config=config_hindi).strip()
    if( not full_text):
        return "", "", "", ""    
    voter_id_img = image[int(0.04*h):int(0.18*h), int(0.6*w):int(0.98*w)]
    voter_id = pytesseract.image_to_string(voter_id_img, lang='eng', config=config_hindi).strip()

    
    # Extract age and house number using text-based approach
    age = extract_age_from_full_text(full_text)
    house_number = extract_house_number_from_full_text(full_text)
    
    # If text-based extraction fails, fall back to ROI-based extraction
    if not age or not house_number:
        # Extract ROIs with better coordinates based on the sample images
        padding = 0.01  # 1% padding
                
        # Age appears after "आयु :" - typically in lower portion
        age_img = image[int(0.65*h):int(0.85*h), int(0.08*w):int(0.25*w)]
        
        # House number appears after "मकान संख्या :" - typically in middle portion
        house_img = image[int(0.45*h):int(0.65*h), int(0.25*w):int(0.85*w)]

        # Create variants for ensemble processing
        age_variants = create_image_variants(age_img, target_height=100)
        house_variants = create_image_variants(house_img, target_height=100)
        
        # Use ensemble approach as fallback
        if not age:
            age = extract_age_ensemble(age_variants)
        if not house_number:
            house_number = extract_house_number_ensemble(house_variants)
    return full_text, voter_id, age, house_number

def create_image_variants(img, target_height=100):
    """
    Create multiple preprocessed variants of the same image for ensemble OCR
    """
    variants = []
    
    # Convert to grayscale if needed
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    
    # Resize image to improve OCR accuracy
    h, w = gray.shape
    if h < target_height:
        scale = target_height / h
        new_w = int(w * scale)
        gray = cv2.resize(gray, (new_w, target_height), interpolation=cv2.INTER_CUBIC)
    
    # Variant 1: Adaptive thresholding with Gaussian blur
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    adaptive_thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY, 11, 2)
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(adaptive_thresh, cv2.MORPH_CLOSE, kernel)
    variants.append(cleaned)
    
    # Variant 2: OTSU thresholding
    _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(otsu_thresh)
    
    # Variant 3: Enhanced contrast with adaptive threshold
    enhanced = cv2.equalizeHist(gray)
    enhanced_blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
    enhanced_thresh = cv2.adaptiveThreshold(enhanced_blurred, 255, 
                                          cv2.ADAPTIVE_THRESH_MEAN_C, 
                                          cv2.THRESH_BINARY, 9, 4)
    variants.append(enhanced_thresh)
    
    # Variant 4: Bilateral filter + threshold
    bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
    _, bilateral_thresh = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(bilateral_thresh)
    
    # Variant 5: Sharpened image
    kernel_sharpen = np.array([[-1,-1,-1],
                              [-1, 9,-1],
                              [-1,-1,-1]])
    sharpened = cv2.filter2D(gray, -1, kernel_sharpen)
    _, sharp_thresh = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(sharp_thresh)
    
    return variants


def extract_age_ensemble(image_variants):
    """
    Extract age using ensemble approach with validation
    """
    configs = [
        '--oem 1 --psm 8 tessedit_char_whitelist=0123456789',
        '--oem 3 --psm 8 tessedit_char_whitelist=0123456789',
        '--oem 1 --psm 13 tessedit_char_whitelist=0123456789',
        '--oem 1 --psm 10 tessedit_char_whitelist=0123456789',
        '--oem 1 --psm 6 tessedit_char_whitelist=0123456789',
    ]
    
    results = []
    
    for variant in image_variants:
        for config in configs:
            try:
                result = pytesseract.image_to_string(variant, lang='eng', config=config).strip()
                # Extract only digits
                digits = re.sub(r'[^0-9]', '', result)
                if validate_age(digits):
                    results.append(digits)
            except:
                continue
    
    if results:
        # Return most common valid result
        return max(set(results), key=results.count)
    return ""

def validate_age(age_str):
    """
    Validate age (reasonable range: 18-120)
    """
    if not age_str or not age_str.isdigit():
        return False
    
    age = int(age_str)
    return 18 <= age <= 120

def extract_house_number_ensemble(image_variants):
    """
    Extract house number - capture complete text including Hindi words
    """
    configs = [
        '--oem 1 --psm 8',
        '--oem 3 --psm 8',
        '--oem 1 --psm 13',
        '--oem 1 --psm 7',
        '--oem 1 --psm 6',
        '--oem 1 --psm 8 tessedit_char_whitelist=0123456789०१२३४५६७८९',  # Only numerals
    ]
    
    results = []
    hindi_text_results = []
    
    for variant in image_variants:
        for config in configs:
            try:
                # Get confidence scores for different language attempts
                for lang in ['hin+eng', 'hin', 'eng']:
                    try:
                        # Get result with confidence
                        data = pytesseract.image_to_data(variant, lang=lang, config=config, output_type=pytesseract.Output.DICT)
                        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                        
                        result = pytesseract.image_to_string(variant, lang=lang, config=config).strip()
                        
                        # Clean and process the result
                        cleaned_result = clean_house_number_text(result)
                        
                        # Check if result contains Hindi text (non-numeric characters)
                        has_hindi_text = any('\u0900' <= c <= '\u097F' for c in result if not c.isdigit() and c not in '०१२३४५६७८९')
                        
                        if has_hindi_text and avg_confidence > 70 and cleaned_result:  # Lowered confidence threshold
                            hindi_text_results.append((cleaned_result, avg_confidence))
                        elif cleaned_result and is_numeric_only(cleaned_result):  # Only accept if purely numeric
                            results.append(cleaned_result)
                    except:
                        continue
            except:
                continue
    
    # Prioritize high-confidence Hindi text results
    if hindi_text_results:
        # Sort by confidence and return the highest confidence result
        hindi_text_results.sort(key=lambda x: x[1], reverse=True)
        return hindi_text_results[0][0]
    
    # Fall back to numeric results
    if results:
        # Return most common numeric result
        return max(set(results), key=results.count)
    
    return ""

def clean_house_number_text(text):
    """
    Clean house number text - preserve Hindi text and numbers, remove unwanted characters
    """
    if not text:
        return ""
    
    # Remove excessive whitespace and clean up
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Remove common OCR artifacts and noise characters
    noise_chars = ['|', '_', '-', '~', '`', '^', '*', '+', '=', '[', ']', '{', '}', '<', '>', '/', '\\']
    for char in noise_chars:
        cleaned = cleaned.replace(char, '')
    
    # Remove any remaining excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def clean_house_number_numbers_only(text):
    """
    Clean house number text - only keep numbers (Hindi and English)
    """
    if not text:
        return ""
    
    # Convert Hindi numerals to English numerals
    hindi_to_english = {
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
        '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
    }
    
    cleaned = text
    for hindi, english in hindi_to_english.items():
        cleaned = cleaned.replace(hindi, english)
    
    # Extract only numeric characters
    numeric_only = re.sub(r'[^0-9]', '', cleaned)
    
    return numeric_only

def is_numeric_only(text):
    """
    Check if text contains only numeric characters
    """
    if not text:
        return False
    return text.isdigit() and len(text) <= 10  # Reasonable house number length


def test_single_image(img_path, ocr_type="age"):
    """
    Test OCR on a single image file with improved processing
    """
    img = cv2.imread(img_path)
    if img is None:
        print(f"Could not load image: {img_path}")
        return ""
    
    variants = create_image_variants(img, target_height=100)
    
    if ocr_type == "age":
        result = extract_age_ensemble(variants)
    elif ocr_type == "house":
        result = extract_house_number_ensemble(variants)
    elif ocr_type == "voter_id":
        result = extract_voter_id_ensemble(variants)
    else:
        # Generic OCR - use Hindi+English for general text
        config = '--oem 1 --psm 8'
        results = []
        for variant in variants:
            try:
                # Try Hindi+English combination first for general text
                for lang in ['hin+eng', 'hin', 'eng']:
                    res = pytesseract.image_to_string(variant, lang=lang, config=config).strip()
                    if res:
                        results.append(res)
            except:
                continue
        result = max(set(results), key=results.count) if results else ""
    
    print(f"OCR Result for {img_path} ({ocr_type}): '{result}'")
    
    # Save all processed variants for inspection
    for i, variant in enumerate(variants):
        cv2.imwrite(f"processed_{ocr_type}_variant_{i}.jpg", variant)
    
    return result

def extract_voter_id_from_full_text(full_text, image):
    """
    Extract voter ID from full text using pattern matching - no validation
    """
    # Look for voter ID pattern in the full text
    # Indian voter ID: 3 letters + 7 digits (but we'll be more flexible)
    patterns = [
        r'\b[A-Z]{3}[0-9]{7}\b',  # Standard format
        r'\b[A-Z]{2,4}[0-9]{6,8}\b',  # Flexible format
        r'\b[A-Z0-9]{8,12}\b'  # Very flexible alphanumeric
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, full_text.upper())
        if matches:
            return matches[0]
    
    # If not found in full text, try OCR on top-right corner specifically
    h, w = image.shape[:2]
    top_right = image[0:int(0.2*h), int(0.6*w):w]
    
    try:
        config = '--oem 1 --psm 8 tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        top_right_text = pytesseract.image_to_string(top_right, lang='eng', config=config).strip()
        
        # Clean and return whatever is found
        cleaned = re.sub(r'[^A-Z0-9]', '', top_right_text.upper())
        if cleaned and len(cleaned) >= 5:
            return cleaned
            
    except:
        pass
    
    return ""

def extract_age_from_full_text(full_text):
    """
    Extract age from full text by looking for age pattern
    """
    # Look for age after "आयु :" or "Age :"
    patterns = [
        r'आयु\s*[:：]\s*(\d+)',
        r'Age\s*[:：]\s*(\d+)',
        r'आयु\s*(\d+)',
        r'(?:आयु|Age)\s*[:：]?\s*(\d{1,3})'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, full_text)
        if matches:
            age = matches[0]
            if validate_age(age):
                return age
    
    # Also try to find standalone numbers that could be age
    # Look for 2-digit numbers that are reasonable ages
    numbers = re.findall(r'\b(\d{2})\b', full_text)
    for num in numbers:
        if validate_age(num):
            return num
    
    return ""

def extract_house_number_from_full_text(full_text):
    """
    Extract house number from full text - capture complete text including multiple words
    """
    # Enhanced patterns to capture complete house number text including multiple words
    patterns = [
        # Pattern to capture everything after "मकान संख्या :" until newline or specific delimiters
        r'मकान\s*संख्या\s*[:：]\s*([^\n\r]+?)(?=\s*(?:आयु|लिंग|Age|Gender|$))',
        # Backup patterns with more specific word boundaries
        r'मकान\s*संख्या\s*[:：]\s*([^\n\r]{1,50})',
        r'मकान\s*(?:संख्या|नंबर)\s*[:：]?\s*([^\n\r]+?)(?=\s*(?:आयु|लिंग|Age|Gender|$))',
        r'House\s*(?:No|Number)\s*[:：]\s*([^\n\r]+?)(?=\s*(?:आयु|लिंग|Age|Gender|$))',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if matches:
            house_num = matches[0].strip()
            
            # Clean the extracted text
            cleaned_house_num = clean_house_number_text(house_num)
            
            if cleaned_house_num:
                # Check if it contains Hindi characters (non-numeric)
                has_hindi_text = any('\u0900' <= c <= '\u097F' for c in cleaned_house_num if not c.isdigit())
                
                if has_hindi_text:
                    # Return Hindi text as-is (complete text)
                    return cleaned_house_num
                else:
                    # For numeric-only, clean and return
                    numeric_cleaned = clean_house_number_numbers_only(cleaned_house_num)
                    if numeric_cleaned:
                        return numeric_cleaned
    
    # Alternative approach: look for text in lines containing house-related keywords
    house_keywords = ['मकान', 'घर', 'House', 'संख्या']
    lines = full_text.split('\n')
    
    for line in lines:
        for keyword in house_keywords:
            if keyword in line:
                # Try to extract the part after the keyword and colon
                parts = re.split(r'[:：]', line, 1)
                if len(parts) > 1:
                    potential_house_num = parts[1].strip()
                    # Remove any trailing text that looks like other fields
                    potential_house_num = re.sub(r'\s*(?:आयु|लिंग|Age|Gender).*$', '', potential_house_num, flags=re.IGNORECASE)
                    
                    cleaned = clean_house_number_text(potential_house_num)
                    if cleaned and len(cleaned) <= 100:  # Reasonable length limit
                        return cleaned
                
                # Fallback: extract numbers from this line
                numbers = re.findall(r'\d+', line)
                if numbers:
                    # Take the first reasonable number
                    for num in numbers:
                        if 1 <= len(num) <= 6:  # Reasonable house number length
                            return num
    
    return ""

def convert_hindi_numerals(text):
    """
    Convert Hindi numerals to English numerals
    """
    hindi_to_english = {
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
        '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
    }
    
    result = text
    for hindi, english in hindi_to_english.items():
        result = result.replace(hindi, english)
    
    return result

def extract_mixed_numerals(text):
    """
    Extract and standardize numerals from mixed Hindi-English text
    """
    # Convert Hindi numerals to English
    converted = convert_hindi_numerals(text)
    
    # Extract continuous numeric sequences
    numeric_parts = re.findall(r'\d+', converted)
    
    return numeric_parts

def test_batch_accuracy(test_images_folder, expected_results):
    """
    Test OCR accuracy on a batch of images
    """
    results = {}
    total_tests = 0
    correct_results = 0
    
    for filename, expected in expected_results.items():
        img_path = os.path.join(test_images_folder, filename)
        if os.path.exists(img_path):
            ocr_type = expected.get('type', 'age')
            result = test_single_image(img_path, ocr_type)
            expected_value = expected.get('value', '')
            
            is_correct = result == expected_value
            results[filename] = {
                'result': result,
                'expected': expected_value,
                'correct': is_correct
            }
            
            total_tests += 1
            if is_correct:
                correct_results += 1
            
            print(f"{filename}: {'✓' if is_correct else '✗'} Got '{result}', Expected '{expected_value}'")
    
    accuracy = (correct_results / total_tests * 100) if total_tests > 0 else 0
    print(f"\nOverall Accuracy: {accuracy:.1f}% ({correct_results}/{total_tests})")
    
    return results