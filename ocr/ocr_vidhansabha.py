import numpy as np
import cv2
import pytesseract

def extract_text(image_array):
    try:
        # Convert NumPy array to image format suitable for OCR
        if len(image_array.shape) == 2:  # Grayscale image
            img = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
        elif image_array.shape[2] == 4:  # RGBA image
            img = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)
        else:  # Assume BGR if not grayscale
            img = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
        
        # Preprocessing pipeline
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        
        gray = cv2.resize(gray, None, fx=3 , fy=3, 
                             interpolation=cv2.INTER_CUBIC)
        
        # Denoising
        gray = cv2.fastNlMeansDenoising(gray, h=10)
        
        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(gray, 255, 
                                      cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        
        # Invert if needed (white text on black background)
        if np.mean(thresh) > 127:  # if mostly white
            thresh = cv2.bitwise_not(thresh)
        
        # OCR configuration
        custom_config = r'--oem 3 --psm 6 -l eng+hin'
        
        # Perform OCR
        cv2.imwrite("debug_thresh.png", thresh)  # Save for debugging
        text = pytesseract.image_to_string(thresh, config=custom_config)

        if(not text.strip()):
            custom_config = r'--oem 3 --psm 11 -l eng+hin'
            # Perform OCR
            text = pytesseract.image_to_string(thresh, config=custom_config)
        return clean_vidhan_sabha_info(text)
    
    except Exception as e:
        print(f"Error in text extraction: {str(e)}")
        return ""


import re

def clean_vidhan_sabha_info(raw_text):
    # Normalize the text
    text = raw_text.replace('\n', ' ').replace('|', ' ')
    text = re.sub(r'[^\w\s\u0900-\u097F()\-–]', '', text)  # keep only useful chars

    # Fix common OCR issues
    text = text.replace("भागसंख्या", "भाग संख्या")
    text = text.replace("सामान्य", "सामान्य")
    text = text.replace("wT", "सामान्य").replace("eT", "सामान्य").replace("aT", "")
    text = re.sub(r'\s+', ' ', text).strip()

    # Find Vidhan Sabha number, name and reservation
    vs_match = re.search(r'(\d{1,3})\s*[-–]?\s*([\u0900-\u097F\s]{2,})\s*\(?([^)]+)?\)?', text)
    
    # Extract bhag number from the last word/number in the string
    words = text.split()
    bhag = ""
    if words:
        last_word = words[-1]
        # Check if last word is a number (bhag sankhya)
        if last_word.isdigit():
            bhag = last_word
        else:
            # Look for any number at the end of the string
            bhag_match = re.search(r'(\d+)\s*$', text)
            if bhag_match:
                bhag = bhag_match.group(1)

    if vs_match:
        num = vs_match.group(1)
        name = vs_match.group(2).strip()
        reservation = vs_match.group(3) or ""
    else:
        return None  # Vidhan Sabha not found

    name = re.sub(r'\s+', '_', name)
    reservation = re.sub(r'\s+', '_', reservation.strip())

    if not reservation:
        reservation = "सामान्य"  # default fallback

    # Final output
    final = f"{num}_{name}_{bhag}".strip("_")
    return final