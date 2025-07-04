from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import os
import json
from db_and_save import save_entry_to_db_and_image


def process_folder(folder_path, progress_callback=None, log_callback=None, pdf_progress_callback=None):
    import os
    import time
    from PyPDF2 import PdfReader



    # Detect PDF files
    pdf_files = []
    try:
        all_files = os.listdir(folder_path)
        for file in all_files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(folder_path, file))
    except Exception as e:
        if log_callback:
            log_callback(f"❌ Error reading folder: {e}")
        return []

    if not pdf_files:
        if log_callback:
            log_callback("❌ No PDF files found in the selected folder")
        return []

    total_start_time = time.time()

    pdf_files.sort()
    all_entries = []

    if log_callback:
        log_callback(f"📁 Found {len(pdf_files)} PDF files to process")
        for i, pdf_file in enumerate(pdf_files, 1):
            log_callback(f"  {i}. {os.path.basename(pdf_file)}")

    if pdf_progress_callback:
        for pdf_path in pdf_files:
            pdf_progress_callback(os.path.basename(pdf_path))

    for pdf_index, pdf_path in enumerate(pdf_files):
        pdf_name = os.path.basename(pdf_path)
        current_pdf_num = pdf_index + 1

        if log_callback:
            log_callback(f"\n📄 Processing PDF {current_pdf_num}/{len(pdf_files)}: {pdf_name}")

        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages) - 3

            pages_processed = 0

            def pdf_specific_progress_callback(gd, gt, pi, lb, tb):
                nonlocal pages_processed
                if lb == tb and lb == 30:
                    pages_processed += 1
                if progress_callback:
                    progress_callback(current_pdf_num, len(pdf_files), pdf_name, pages_processed, total_pages)

            entries, _ = process_pdf(
                pdf_path=pdf_path,
                progress_callback=pdf_specific_progress_callback,
                log_callback=log_callback,
                is_folder_processing=True
            )

            if progress_callback:
                progress_callback(current_pdf_num, len(pdf_files), pdf_name, total_pages, total_pages)

            all_entries.extend(entries)

            if log_callback:
                log_callback(f"✅ Completed {pdf_name}: {len(entries)} entries extracted")

        except Exception as e:
            if log_callback:
                log_callback(f"❌ Error processing {pdf_name}: {str(e)}")
            continue

    output_json = "output/combined_result.json"
    os.makedirs("output", exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    
    total_end_time = time.time()

    total_execution_time_secs = (total_end_time - total_start_time) % 60
    total_execution_time_minutes = (total_end_time - total_start_time) / 60
    if log_callback:
        log_callback(f"\n✅ All PDFs processed. Combined results saved to {output_json}")
        log_callback(f"📊 Total entries extracted: {len(all_entries)}")
        log_callback(f"⏱️ Total execution time: {total_execution_time_minutes:.0f} Minutes {total_execution_time_secs:.2f} seconds")



    return all_entries


def process_pdf(pdf_path="data/input.pdf", progress_callback=None, log_callback=None, is_folder_processing=False):
    import time
    import cv2
    import numpy as np
    from PIL import Image
    from PyPDF2 import PdfReader
    from pdf2image import convert_from_path
    from config import POPPLER_PATH
    from ocr.preprocessing import preprocess_image, remove_boxes
    from ocr.extract_fields import extract_fields
    from ocr.page_cropper import crop_10x3_grid
    from ocr.ocr_engine_2  import (perform_ocr,extract_seq)
    from ocr.ocr_vidhansabha import extract_text


    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    if log_callback:
        log_callback(f"📄 Processing PDF: {pdf_name}")
    output_json = f"output/{pdf_name}_result.json"
    os.makedirs("temp_crops", exist_ok=True)
    start_time = time.time()
    offset = 0
    reader = PdfReader(pdf_path)

    

    # # Extract Vidhan Sabha Info
    # firstPage = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1, poppler_path=POPPLER_PATH)
    # firstPageImg = cv2.cvtColor(np.array(firstPage[0]), cv2.COLOR_RGB2BGR)
    # h, w = firstPageImg.shape[:2]
    # image = firstPageImg[int(0.085 * h):int(0.11 * h), int(0.384 * w):int(0.98 * w)]
    # os.makedirs("output/first_pages", exist_ok=True)
    # cv2.imwrite(f"output/first_pages/{pdf_name}_firstpage.jpg", image)

    # vidhansabha = extract_text(image)
    # if log_callback:
    #     log_callback(f"📍 Extracted Vidhan Sabha Info: {vidhansabha}")

    images = convert_from_path(pdf_path, dpi=300, first_page=3, last_page=len(reader.pages) - 1, poppler_path=POPPLER_PATH)

    total_expected_entries = len(images) * 30
    all_entries = []
    entry_count = 0
    lock = threading.Lock()

    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "Password@123**",
        "database": "voter_db",
    }

    def process_single_page(page_index, page_img):
        import pytesseract
        should_break = False
        nonlocal entry_count
        page_num = page_index + 3
        entries = []
        nonlocal offset
        if log_callback and not is_folder_processing:
            log_callback(f"📄 Page {page_num}: Started")

        img_cv2 = cv2.cvtColor(np.array(page_img), cv2.COLOR_RGB2BGR)
        boxes = crop_10x3_grid(img_cv2)

        for i, box in enumerate(boxes):
            if should_break:
                if log_callback and not is_folder_processing:
                    log_callback(f"❌ Stopping early on page {page_num} due to empty fields.")
                break
            sequenceOCR = extract_seq(box["image"])
    
    
            img_no_border = remove_boxes(box["image"])
            result = perform_ocr(img_no_border)

            required_fields = ['Name', 'relation', 'relationName', 'houseNumber', 'Age']
            is_empty = all(not result.get(field) for field in required_fields)

            # Handle skipping and early stop based on empty fields
            if is_empty:
                    should_break = True
                    break
                
            with lock:
                entry_count += 1
                if progress_callback:
                    progress_callback(entry_count, total_expected_entries, page_index, i + 1, 30)

            sequence = (page_num - 3) * 30 + (box["row"] - 1) * 3 + box["col"] - offset

            save_entry_to_db_and_image(
                result=result,
                vidhansabha=pdf_name,
                sequence=sequence,
                sequenceOCR=sequenceOCR,
                image=box["image"],
                db_config=db_config,
            )

            entries.append({
                "sequence": sequence,
                "sequenceOCR": sequenceOCR,
                "page": page_num,
                "row": box["row"],
                "col": box["col"],
                "vidhansabha": pdf_name,
                "text": result,
            })


        if log_callback and not is_folder_processing:
            log_callback(f"✅ Page {page_num}: Done ({len(entries)} entries)")

        return entries

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(process_single_page, i, img) for i, img in enumerate(images)]
        for f in as_completed(futures):
            result = f.result()
            all_entries.extend(result)

    os.makedirs("output", exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    end_time = time.time()
    if log_callback:
        log_callback(f"💾 JSON saved to {output_json}")
        log_callback(f"⏱️ Execution Time: {end_time - start_time:.2f} sec")
        log_callback(f"📊 Total entries extracted: {len(all_entries)}")

    return all_entries, len(images)


if __name__ == "__main__":
    import sys

    def dummy_progress_callback(global_done, global_total, page_index, local_box_num, total_boxes):
        print(f"[Page {page_index + 3}] Box {local_box_num}/{total_boxes} | Total Progress: {global_done}/{global_total}")

    if len(sys.argv) > 1:
        if os.path.isdir(sys.argv[1]):
            print(f"Processing folder: {sys.argv[1]}")
            process_folder(sys.argv[1], log_callback=print)
        elif sys.argv[1].lower().endswith('.pdf'):
            print(f"Processing PDF: {sys.argv[1]}")
            process_pdf(
                pdf_path=sys.argv[1],
                progress_callback=dummy_progress_callback,
                log_callback=print
            )
        else:
            print("Invalid argument. Please provide a PDF file or folder path.")
    else:
        print("Starting default PDF processing...")
        process_pdf(
            pdf_path="data/input.pdf",
            progress_callback=dummy_progress_callback,
            log_callback=print
        )
