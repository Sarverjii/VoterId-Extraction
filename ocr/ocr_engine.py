import pytesseract
from config import TESSERACT_PATH
import cv2
import time
import numpy as np
import os


pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def perform_ocr(image):
    os.makedirs("crops", exist_ok=True)  # Create directory if it doesn't exist
    h, w = image.shape[:2]
    # Voter ID ROI
    voter_id_img = image[int(0.04*h):int(0.18*h), int(0.6*w):int(0.98*w)]
    # Age ROI
    age_img = image[int(0.58*h):int(0.7*h), int(0.12*w):int(0.17*w)]
    # houseNumber ROI
    house_img = image[int(0.47*h):int(0.59*h), int(0.226*w):int(0.5*w)]

    

    config = '--oem 1 --psm 6'
    full_text = pytesseract.image_to_string(image, lang='hin', config=config).strip()
    voter_id = pytesseract.image_to_string(voter_id_img, lang='eng', config=config).strip()
    age = pytesseract.image_to_string(age_img, lang='eng', config='--oem 3 --psm 8 tessedit_char_whitelist=0123456789').strip()    
    house_number = pytesseract.image_to_string(house_img, lang='hin', config='--oem 3 --psm 11' ).strip()
    cv2.imwrite(f"crops/{voter_id}-voterId.jpg", voter_id_img)
    cv2.imwrite(f"crops/{voter_id}-age.jpg", age_img)
    cv2.imwrite(f"crops/{voter_id}-house.jpg", house_img)
    return full_text, voter_id, age, house_number

