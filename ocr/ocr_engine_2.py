import re
import pytesseract
import cv2
import numpy as np
from PIL import Image




def perform_ocr(image):
    voterId = extract_voterId_2(image)
    full_text = full_ocr(image)

    # print("Full Text \n" + full_text)
    age = extract_age(image)
    houseNumber = extract_houseNumber(image)
    data = parse_voter_info(full_text)
    # print("Data from Parser : ")
    # for key, value in data.items():
    #             print(f"{key:>12}: {value}")


    # print("Final Data")

    name = data.get('name')
    if not name:
        name = extract_name(image);
        if not name:
            name = "Name Unavailable"


    if not age:
        age = data.get("Age")

    if age:
        age = devanagari_to_english_digits(data["Age"])


    if age.strip() != '':
        if int(age) < 18:
            if int(age) < 8 and int(age) > 0:
                age = age + "1"
            if age == '0':
                age = "1" + age
            else:
                newage = extract_age_fallback_1_sensitive(image)
                if newage.strip() != '':
                    if int(newage) < 18:
                        age = age + "1"
                    else:
                        age = newage
    if not houseNumber: 
        houseNumber = data.get("houseNumber")

    voter_data = {
        "voterId": voterId,
        "name" : name,
        'relationName' : data.get('relationName'),
        'relation' : data.get('relation'),
        "houseNumber": houseNumber,
        "Age": age,
        "gender" : data.get("gender")
    }

    return voter_data

def devanagari_to_english_digits(text):
    devanagari_digits = '०१२३४५६७८९'
    english_digits = '0123456789'
    trans = str.maketrans(devanagari_digits, english_digits)
    return text.translate(trans)




def parse_voter_info(text):
    """
    Super robust parser for voter information strings.
    Handles OCR errors for relation (पति/पिता) and gender (पुरुष/महिला).
    """
    # Clean and normalize the input
    text = text.replace('\\n', '\n').strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    data = {
        "name": "",
        "relationName": "",
        "relation": "",
        "houseNumber": "",
        "Age": "",
        "gender": ""
    }
    
    def normalize_relation(text):
        """Normalize relation with OCR error handling"""
        text = text.strip().lower()
        
        # Remove common punctuation
        text = re.sub(r'[।.,:;]+', '', text)
        
        # पति variations (OCR errors)
        pati_patterns = [
            r'पति', r'पती', r'पतर', r'पत्र', r'पि?ति', r'पि?ती', 
            r'पिति', r'पिती', r'पत्ति', r'पत्ती', r'पति?', r'पती?',
            r'पिि?ति', r'पिि?ती', r'पत्ि?ति', r'पत्ि?ती'
        ]
        
        # पिता variations (OCR errors)
        pita_patterns = [
            r'पिता', r'पििता', r'पीता', r'पीिता', r'पि?ता', r'पीि?ता',
            r'पितिा', r'पीतिा', r'पि?तिा', r'पीि?तिा', r'पिता?', r'पीता?',
            r'पि?ि?ता', r'पि?ि?ता?'
        ]
        
        # अन्य variations (OCR errors)
        anya_patterns = [
            r'अन्य', r'अन्या', r'अन्यि', r'अन्यि?', r'अन्या?', r'अन्ि?य',
            r'अन्ि?या', r'अन्ि?यि', r'अन्ि?यि?', r'अन्ि?या?', r'अि?न्य',
            r'अि?न्या', r'अि?न्यि', r'अि?न्यि?', r'अि?न्या?'
        ]
        
        # Check for पति patterns
        for pattern in pati_patterns:
            if re.search(pattern, text):
                return 'पति'
        
        # Check for पिता patterns
        for pattern in pita_patterns:
            if re.search(pattern, text):
                return 'पिता'
        
        # Check for अन्य patterns
        for pattern in anya_patterns:
            if re.search(pattern, text):
                return 'अन्य'
        
        # Fallback: if contains 'प' and 'त' and 'ि', likely पति
        if 'प' in text and 'त' in text and 'ि' in text and len(text) <= 6:
            return 'पति'
        
        # Fallback: if contains 'प' and 'त' and 'ा', likely पिता
        if 'प' in text and 'त' in text and 'ा' in text and len(text) <= 6:
            return 'पिता'
        
        # Fallback: if contains 'अ' and 'न' and 'य', likely अन्य
        if 'अ' in text and 'न' in text and 'य' in text and len(text) <= 6:
            return 'अन्य'
        
        return text  # Return original if no match
    
    def normalize_gender(text):
        """Normalize gender with OCR error handling"""
        text = text.strip().lower()
        
        # Remove common punctuation
        text = re.sub(r'[।.,:;]+', '', text)
        
        # पुरुष variations (OCR errors)
        purush_patterns = [
            r'पुरुष', r'पुरुि?ष', r'पुरुि?ि?ष', r'पुरुष?', r'पुरुि?ष?',
            r'पुरुि?', r'पुरुि?ि?', r'पुरुष।?', r'पुरुि?ष।?',
            r'पुरुष्', r'पुरुि?ष्', r'पुरुि?ि?ष्', r'पुरुष्?',
            r'पुरुि?ष्?', r'पुरुि?ि?ष्?', r'पुरुष।', r'पुरुि?ष।',
            r'पुरुि?ि?ष।', r'पुरुष।?', r'पुरुि?ष।?', r'पुरुि?ि?ष।?',
            r'पुरुष्।', r'पुरुि?ष्।', r'पुरुि?ि?ष्।', r'पुरुष्।?',
            r'पुि?रुष', r'पुि?रुि?ष', r'पुि?रुि?ि?ष', r'पुि?रुष?',
            r'पुि?रुि?ष?', r'पुि?रुि?ि?ष?', r'पुि?रुष।', r'पुि?रुि?ष।',
            r'पुि?रुि?ि?ष।', r'पुि?रुष।?', r'पुि?रुि?ष।?', r'पुि?रुि?ि?ष।?',
            r'पुि?रुष्', r'पुि?रुि?ष्', r'पुि?रुि?ि?ष्', r'पुि?रुष्?',
            r'पुि?रुि?ष्?', r'पुि?रुि?ि?ष्?', r'पुि?रुष्।', r'पुि?रुि?ष्।',
            r'पुि?रुि?ि?ष्।', r'पुि?रुष्।?', r'पुि?रुि?ष्।?', r'पुि?रुि?ि?ष्।?'
        ]
        
        # महिला variations (OCR errors)
        mahila_patterns = [
            r'महिला', r'महिि?ला', r'महिि?ि?ला', r'महिला?', r'महिि?ला?',
            r'महिि?ि?ला?', r'महिला।', r'महिि?ला।', r'महिि?ि?ला।',
            r'महिला।?', r'महिि?ला।?', r'महिि?ि?ला।?', r'महिला्',
            r'महिि?ला्', r'महिि?ि?ला्', r'महिला्?', r'महिि?ला्?',
            r'महिि?ि?ला्?', r'महिला्।', r'महिि?ला्।', r'महिि?ि?ला्।',
            r'महिला्।?', r'महिि?ला्।?', r'महिि?ि?ला्।?', r'मि?हिला',
            r'मि?हिि?ला', r'मि?हिि?ि?ला', r'मि?हिला?', r'मि?हिि?ला?',
            r'मि?हिि?ि?ला?', r'मि?हिला।', r'मि?हिि?ला।', r'मि?हिि?ि?ला।',
            r'मि?हिला।?', r'मि?हिि?ला।?', r'मि?हिि?ि?ला।?', r'मि?हिला्',
            r'मि?हिि?ला्', r'मि?हिि?ि?ला्', r'मि?हिला्?', r'मि?हिि?ला्?',
            r'मि?हिि?ि?ला्?', r'मि?हिला्।', r'मि?हिि?ला्।', r'मि?हिि?ि?ला्।',
            r'मि?हिला्।?', r'मि?हिि?ला्।?', r'मि?हिि?ि?ला्।?'
        ]
        
        # Check for पुरुष patterns
        for pattern in purush_patterns:
            if re.search(pattern, text):
                return 'पुरुष'
        
        # Check for महिला patterns
        for pattern in mahila_patterns:
            if re.search(pattern, text):
                return 'महिला'
        
        # Fallback logic for पुरुष
        if ('प' in text and 'र' in text and 'ष' in text) or \
           ('प' in text and 'र' in text and 'स' in text) or \
           ('प' in text and 'ु' in text and 'र' in text):
            return 'पुरुष'
        
        # Fallback logic for महिला
        if ('म' in text and 'ह' in text and 'ल' in text) or \
           ('म' in text and 'ि' in text and 'ल' in text) or \
           ('म' in text and 'ा' in text and 'ल' in text):
            return 'महिला'
        
        return text  # Return original if no match
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Parse name (primary name, not relation name)
        if re.search(r'नाम\s*[:;ः]', line) and not re.search(r'का\s*नाम', line):
            match = re.search(r'नाम\s*[:;ः]\s*(.+?)(?:\s*$)', line)
            if match and not data["name"]:
                data["name"] = match.group(1).strip()
        
        # Parse relation and relation name
        elif re.search(r'का\s*नाम', line):
            # Extract relation name (everything after 'का नाम')
            rel_name_match = re.search(r'का\s*नाम\s*[:;ः]\s*(.+?)(?:\s*$)', line)
            if rel_name_match:
                data["relationName"] = rel_name_match.group(1).strip()
            
            # Extract relation type (before 'का नाम')
            before_ka_naam = re.search(r'(\S+)\s*का\s*नाम', line)
            if before_ka_naam:
                raw_relation = before_ka_naam.group(1).strip()
                data["relation"] = normalize_relation(raw_relation)
        
        # Parse अन्य relation (direct format: अन्य: name)
        elif re.search(r'अन्य\s*[:;ः]', line):
            # Extract relation name after अन्य
            anya_match = re.search(r'अन्य\s*[:;ः]\s*(.+?)(?:\s*$)', line)
            if anya_match:
                data["relationName"] = anya_match.group(1).strip()
                data["relation"] = 'अन्य'
        
        # Parse house number - handle typos like 'सकान' instead of 'मकान' and complex numbers
        elif re.search(r'[मस]कान\s*संख्या', line):
            house_match = re.search(r'[मस]कान\s*संख्या\s*[:;ः]\s*([0-9/]*)', line)
            if house_match:
                house_num = house_match.group(1).strip()
                data["houseNumber"] = house_num if house_num else ""
        
        # Parse age and gender
        elif re.search(r'आयु', line) and re.search(r'लिंग', line):
            # Extract age
            age_match = re.search(r'आयु\s*[:;ः]\s*(\d+)[।.]?', line)
            if age_match:
                data["Age"] = age_match.group(1).strip()
            
            # Extract gender
            gender_match = re.search(r'लिंग\s*[:;ः]\s*(\S+)', line)
            if gender_match:
                raw_gender = gender_match.group(1).strip()
                data["gender"] = normalize_gender(raw_gender)
        
        # Handle standalone age or gender lines
        elif re.search(r'आयु\s*[:;ः]', line) and not data["Age"]:
            age_match = re.search(r'आयु\s*[:;ः]\s*(\d+)[।.]?', line)
            if age_match:
                data["Age"] = age_match.group(1).strip()
        
        elif re.search(r'लिंग\s*[:;ः]', line) and not data["gender"]:
            gender_match = re.search(r'लिंग\s*[:;ः]\s*(\S+)', line)
            if gender_match:
                raw_gender = gender_match.group(1).strip()
                data["gender"] = normalize_gender(raw_gender)
    
    # Post-processing: Clean up extracted data
    for key in data:
        if isinstance(data[key], str):
            # Remove trailing punctuation marks
            data[key] = re.sub(r'[।.,:;]+$', '', data[key]).strip()
    
    return data



def extract_name(image):
    h,w = image.shape[:2]
    name_img = image[int(0.23*h):int(0.36*h), int(0.11*w):int(0.65*w)]

    config = '--oem 3 --psm 6'
    text =  pytesseract.image_to_string(name_img, lang='hin', config=config).strip()
    if not text:
        config = '--oem 3 --psm 11'
        text =  pytesseract.image_to_string(name_img, lang='hin', config=config).strip()
    if not text:
        config = '--oem 3 --psm 8'
        text =  pytesseract.image_to_string(name_img, lang='hin', config=config).strip()
    return text


def full_ocr(image):
    h,w = image.shape[:2]
    image = image[int(0.2*h):, :]
    config = '--oem 3 --psm 11'
    text =  pytesseract.image_to_string(image, lang='hin', config=config).strip()
    return text

def extract_seq(image): 
    h, w = image.shape[:2]

    # Crop rough box area
    sequence_img = image[int(0.05*h):int(0.25*h), int(0.2*w):int(0.35*w)]
    gray = cv2.cvtColor(sequence_img, cv2.COLOR_BGR2GRAY)

    # Binary inverse for contour detection
    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Find largest box
    largest_box = max(contours, key=cv2.contourArea, default=None)
    if largest_box is not None:
        x, y, bw, bh = cv2.boundingRect(largest_box)
        padding = 5
        x1 = max(x + padding, 0)
        y1 = max(y + padding, 0)
        x2 = min(x + bw - padding, sequence_img.shape[1])
        y2 = min(y + bh - padding-5, sequence_img.shape[0])
        digit_roi = sequence_img[y1:y2, x1:x2]
    else:
        digit_roi = sequence_img

    # Resize for better OCR (2x)
    digit_roi = cv2.resize(digit_roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # Convert to grayscale and binary
    gray = cv2.cvtColor(digit_roi, cv2.COLOR_BGR2GRAY) if len(digit_roi.shape) == 3 else digit_roi
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Clean thin lines (box remnants)
    kernel = np.ones((2, 2), np.uint8)
    processed = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    # cv2.imwrite("sequence.jpg", processed)



    # OCR config
    config = "--oem 3 --psm 6"
    text = pytesseract.image_to_string(processed, config=config).strip()
    if not text:
        config = "--oem 3 --psm 11"
        text = pytesseract.image_to_string(processed, config=config).strip()
    if not text:
        config = "--oem 1 --psm 6"
        text = pytesseract.image_to_string(processed, config=config).strip()


    text = text.replace('S', '5') \
                       .replace('s', '5') \
                       .replace('$', '5') \
                       .replace('?', '7') \
                       .replace('|', '1') \
                       .replace('॥', '1') \
                       .replace(']', '1') \
                       .replace(')', '1') \
                       .replace('(', '1') \
                       .replace('[', '1')
    # print(f"Extracted text: '{text}'")
    return text




def extract_voterId_2(image):
    h, w = image.shape[:2]
    voterId_img = image[int(0.04 * h):int(0.18 * h), int(0.6 * w):int(0.98 * w)]

    gray = cv2.cvtColor(voterId_img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Patterns
    pattern1 = re.compile(r'^[A-Z]{3}[0-9]{7}$')
    pattern2 = re.compile(r'^[A-Z]{2}/[0-9]{2}/[0-9]{3}/[0-9]{6}$')

    # Best configs for single line alphanumeric strings
    config_list = [
        '--oem 3 --psm 7',
        '--oem 3 --psm 6',
        '--oem 1 --psm 7',
        '--oem 1 --psm 8',
        '--oem 3 --psm 13',
        '--oem 1 --psm 6',
        '--oem 1 --psm 11',
        '--oem 1 --psm 12',
        '--oem 1 --psm 9'
    ]
    text = ""
    cleaned = ""
    for config in config_list:
        text = pytesseract.image_to_string(thresh, lang='eng', config=config).strip()

        # Remove lowercase and unwanted characters (allow only A-Z, 0-9, /, -)
        cleaned = re.sub(r'[a-z]', '', text)                   # remove lowercase
        cleaned = re.sub(r'[^A-Z0-9/]', '', cleaned)          # allow only valid characters
        cleaned = cleaned.replace(" ", "")                     # remove spaces

        # Check for valid pattern
        if pattern1.fullmatch(cleaned) or pattern2.fullmatch(cleaned):
            return cleaned

    # If no valid pattern found, return empty string
    return cleaned






def extract_voterId(image):
    h, w = image.shape[:2]
    voterId_img = image[int(0.04 * h):int(0.18 * h), int(0.6 * w):int(0.98 * w)]

    gray = cv2.cvtColor(voterId_img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Patterns
    pattern1 = re.compile(r'^[A-Z]{3}[0-9]{7}$')
    pattern2 = re.compile(r'^[A-Z]{2}/[0-9]{2}/[0-9]{3}/[0-9]{6}$')

    # Best configs for single line alphanumeric strings
    config_list = [
        '--oem 3 --psm 7',
        '--oem 3 --psm 6',
        '--oem 1 --psm 7',
        '--oem 1 --psm 8',
        '--oem 3 --psm 13'
    ]
    text = ""
    cleaned = ""
    for config in config_list:
        text = pytesseract.image_to_string(thresh, lang='eng', config=config).strip()

        # Remove lowercase and unwanted characters (allow only A-Z, 0-9, /, -)
        cleaned = re.sub(r'[a-z]', '', text)                   # remove lowercase
        cleaned = re.sub(r'[^A-Z0-9/]', '', cleaned)          # allow only valid characters
        cleaned = cleaned.replace(" ", "")                     # remove spaces

        # Check for valid pattern
        if pattern1.fullmatch(cleaned) or pattern2.fullmatch(cleaned):
            return cleaned

    # If no valid pattern found, return empty string
    return cleaned







def extract_houseNumber(image):
    h, w = image.shape[:2]
    house_img = image[int(0.47*h):int(0.59*h), int(0.226*w):int(0.5*w)]

    # Preprocessing
    gray = cv2.cvtColor(house_img, cv2.COLOR_BGR2GRAY)

    # Resize to improve clarity of thin characters like '1'
    resized = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

    # Slight blur to smooth artifacts
    blurred = cv2.GaussianBlur(resized, (3, 3), 0)

    # Thresholding
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # OCR Config (treat as digits-only mode)
    config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'

    # Use image_to_data to get word-level confidence
    data = pytesseract.image_to_data(thresh, lang='eng', config=config, output_type=pytesseract.Output.DICT)

    text = ""
    confidences = []

    for i in range(len(data['text'])):
        word = data['text'][i].strip()
        if not word:
            continue

        try:
            conf = int(data['conf'][i])
        except ValueError:
            conf = 0

        if conf > 0:
            # Fix common OCR misreads
            word = word.replace('S', '5') \
                       .replace('s', '5') \
                       .replace('$', '5') \
                       .replace('?', '7') \
                       .replace('|', '1') \
                       .replace('॥', '1') \
                       .replace(']', '1') \
                       .replace('[', '1')
            text += word
            confidences.append(conf)

    avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    if avg_conf < 70:
        # print(f"[LOW CONFIDENCE] House Number: '{text}' at {avg_conf}%")
        text = ""

    return text



def extract_age(image):
    h, w = image.shape[:2]
    age_img = image[int(0.58*h):int(0.7*h), int(0.12*w):int(0.17*w)]

    gray = cv2.cvtColor(age_img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    _, thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    config = '--oem 3 --psm 11'

    # Use image_to_data for confidence
    data = pytesseract.image_to_data(thresh, lang='eng', config=config, output_type=pytesseract.Output.DICT)

    text = ""
    confidences = []

    for i in range(len(data['text'])):
        word = data['text'][i].strip()
        conf = int(data['conf'][i])

        if word and conf > 0:
            word = word.replace('S', '5').replace('s', '5').replace('$', '5').replace('?', '7')
            text += word
            confidences.append(conf)

    avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0


    if(avg_conf<70):
        # print(f"Age Extracted : {text}, Confidence: {avg_conf}%")
        text = ""

    return text


def extract_age_fallback_1_sensitive(image):
    h, w = image.shape[:2]
    age_img = image[int(0.58*h):int(0.7*h), int(0.12*w):int(0.17*w)]

    # Grayscale
    gray = cv2.cvtColor(age_img, cv2.COLOR_BGR2GRAY)

    # CLAHE for local contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)

    # Resize
    resized = cv2.resize(enhanced, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # Sharpen slightly
    sharpened = cv2.GaussianBlur(resized, (0, 0), 3)
    sharpened = cv2.addWeighted(resized, 1.5, sharpened, -0.5, 0)

    # Dilation to make '1' more visible
    kernel = np.ones((2, 2), np.uint8)
    dilated = cv2.dilate(sharpened, kernel, iterations=1)

    # Threshold
    _, thresh = cv2.threshold(dilated, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    configs = [
        '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789',
        '--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789',
        '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
    ]

    for config in configs:
        text = pytesseract.image_to_string(thresh, lang='eng', config=config).strip()

        # Clean common misreads
        text = text.replace('I', '1').replace('l', '1').replace('|', '1')
        text = text.replace('S', '5').replace('s', '5').replace('$', '5').replace('?', '7')

        # Only return if valid 1–3 digit number with 1 in it
        if re.fullmatch(r'\d{1,3}', text) and '1' in text:
            return text

    return ""
