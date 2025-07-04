import cv2
import numpy as np



def remove_boxes(image):
    h, w = image.shape[:2]
    result = image.copy()

    # --- Step 1: Fill inner boxes with white ---

    # S. No. box (top-left)
    s_no_y1, s_no_y2 = int(0.04*h), int(0.22*h)
    s_no_x1, s_no_x2 = int(0.015*w), int(0.5*w)
    result[s_no_y1:s_no_y2, s_no_x1:s_no_x2] = 255

    # Photo box (top-right)
    photo_y1, photo_y2 = int(0.21*h), int(0.95*h)
    photo_x1, photo_x2 = int(0.7*w), int(0.98*w)
    result[photo_y1:photo_y2, photo_x1:photo_x2] = 255


    border_thickness = int(0.05 * min(h, w))  # ~2% of smaller dimension

    
    # Top border
    result[0:border_thickness, :] = 255
    # Bottom border
    result[h-border_thickness:h, :] = 255
    # Left border
    result[:, 0:border_thickness] = 255
    # Right border
    result[:, w-border_thickness:w] = 255
    

    return result


def preprocess_image_v1(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)


    # Denoise
    blurred = cv2.GaussianBlur(resized, (3, 3), 0)

     # CLAHE for contrast boosting
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(denoised)


    # Adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        enhanced, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )
    return thresh


def preprocess_image(image):
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Resize: Enlarge for OCR to see finer details
    resized = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # Slight blur to remove grain but keep strokes intact
    blurred = cv2.GaussianBlur(resized, (3, 3), 0)

    # CLAHE for contrast boosting
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(blurred)

    # Adaptive Threshold with softer block size and constant
    binary = cv2.adaptiveThreshold(
        enhanced, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,  # Bigger block handles thick text well
        C=10
    )

    return binary
