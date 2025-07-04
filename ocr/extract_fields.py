from .utils import *

def extract_fields(text, voter_id, age,houseNumber):
    voter_data = {
        "voterId": voter_id,
        "Name": "",
        "relationName": "",
        "relation": "",
        "houseNumber" : houseNumber ,
        "Age": age,
        "Gender": "",
    }

    lines = [clean_line(line) for line in text.split('\n') if line.strip()]
    
    if len(lines) >= 2:
        voter_data["Name"] = extract_after_separator(lines[1]) or lines[1].strip()

    if len(lines) >= 3:
        relation_line = lines[2]
        voter_data["relation"] = detect_relation_type(relation_line)
        voter_data["relationName"] = extract_after_separator(relation_line)

    # if len(lines) >= 4:
    #     numbers = extract_numbers(lines[3])
    #     if numbers:
    #         voter_data["houseNumber"] = numbers[0]

    voter_data["Gender"] = detect_gender(text)
    return voter_data
