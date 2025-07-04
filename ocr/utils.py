import re

def clean_line(line):
    return re.sub(r'\s+', ' ', line.strip())

def extract_after_separator(line, separators=[':',';','।','|','!']):
    for sep in separators:
        if sep in line:
            parts = line.split(sep, 1)
            if len(parts) > 1:
                return parts[1].strip()
    return ""

def extract_numbers(text):
    hindi_to_eng = {'०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
                    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'}
    for hin, eng in hindi_to_eng.items():
        text = text.replace(hin, eng)
    return re.findall(r'\d+', text)

def contains_keyword(text, keywords):
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)

def detect_relation_type(line):
    if 'पिता' in line:
        return 'Father'
    if 'पति' in line:
        return 'Husband'
    return 'पिता'

def detect_gender(text):
    if contains_keyword(text, ['महिला', 'स्त्री']):
        return 'Female'
    if contains_keyword(text, ['पुरुष']):
        return 'Male'
    return 'Male'
