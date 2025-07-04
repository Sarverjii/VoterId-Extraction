from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from db_and_save import save_entry_to_db_and_image


def process_pdf(pdf_path="data/input.pdf", progress_callback=None, log_callback=None):
    import os, time, json, cv2
    import numpy as np
    from PIL import Image
    from PyPDF2 import PdfReader
    from pdf2image import convert_from_path
    from config import POPPLER_PATH
    from ocr.preprocessing import (preprocess_image, remove_boxes)
    from ocr.extract_fields import extract_fields
    from ocr.page_cropper import crop_10x3_grid
    from ocr.ocr_engine_copy import perform_ocr
    from ocr.ocr_vidhansabha import extract_text

    output_json = "output/result.json"
    os.makedirs("temp_crops", exist_ok=True)
    start_time = time.time()

    reader = PdfReader(pdf_path)
    firstPage = convert_from_path(
        pdf_path, dpi=300,
        first_page=1, last_page=1,
        poppler_path=POPPLER_PATH
    )
    firstPageImg = cv2.cvtColor(np.array(firstPage[0]), cv2.COLOR_RGB2BGR)
    h, w = firstPageImg.shape[:2]
    image = firstPageImg[int(0.085 * h):int(0.11 * h), int(0.385 * w):int(0.98 * w)]
    cv2.imwrite("firstpage.jpg", image)

    vidhansabha = extract_text(image)
    if log_callback:
        log_callback(f"Extracted Vidhan Sabha Info: {vidhansabha}")

    images = convert_from_path(
        pdf_path, dpi=300,
        first_page=3,
        last_page=len(reader.pages) - 1,
        poppler_path=POPPLER_PATH
    )

    total_expected_entries = len(images) * 30
    all_entries = []
    entry_count = 0
    lock = threading.Lock()

    # MySQL config (update these values accordingly)
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "Cfs123**",
        "database": "voter_db",
    }

    def process_single_page(page_index, page_img):
        should_break = False
        nonlocal entry_count
        page_num = page_index + 3
        entries = []

        if log_callback:
            log_callback(f"📄 Page {page_num}: Started")

        img_cv2 = cv2.cvtColor(np.array(page_img), cv2.COLOR_RGB2BGR)
        boxes = crop_10x3_grid(img_cv2)

        for i, box in enumerate(boxes):
            if should_break:
                if log_callback:
                    log_callback(f"❌ Stopping early on page {page_num} due to empty fields.")
                break

            img_no_border = remove_boxes(box["image"])
            processed = preprocess_image(img_no_border)

            text, voter_id, age, houseNumber = perform_ocr(img_no_border)
            result = extract_fields(text, voter_id, age, houseNumber)

            required_fields = ['voterId', 'Name', 'relation', 'relationName', 'houseNumber', 'Age']
            if all(not result.get(field) for field in required_fields):
                should_break = True
                return entries

            with lock:
                entry_count += 1
                if progress_callback:
                    progress_callback(
                        entry_count,
                        total_expected_entries,
                        page_index,
                        i + 1,
                        30
                    )

            sequence = (page_num - 3) * 10 + (box["col"] - 1) * 3 + box["row"]

            save_entry_to_db_and_image(
                result=result,
                vidhansabha=vidhansabha,
                page=page_num,
                row=box["row"],
                col=box["col"],
                image=box["image"],
                db_config=db_config
            )

            entries.append({
                "sequence": sequence,
                "page": page_num,
                "row": box["row"],
                "col": box["col"],
                "vidhansabha": vidhansabha,
                "text": result,
            })

        if log_callback:
            log_callback(f"✅ Page {page_num}: Done")

        return entries

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_single_page, i, img) for i, img in enumerate(images)]
        for f in as_completed(futures):
            result = f.result()
            all_entries.extend(result)

    os.makedirs("output", exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    end_time = time.time()
    if log_callback:
        log_callback(f"\n✅ JSON saved to {output_json}")
        log_callback(f"⏱️ Execution Time: {end_time - start_time:.2f} sec")

    return all_entries, len(images)


if __name__ == "__main__":
    print("Starting PDF processing...")

    def dummy_progress_callback(global_done, global_total, page_index, local_box_num, total_boxes):
        print(f"[Page {page_index + 3}] Box {local_box_num}/{total_boxes} | Total Progress: {global_done}/{global_total}")

    process_pdf(
        pdf_path="data/input.pdf",
        progress_callback=dummy_progress_callback,
        log_callback=print
    )
