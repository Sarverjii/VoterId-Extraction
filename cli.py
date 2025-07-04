import os
from main4 import process_folder

def run_cli_folder_ocr():
    print("🗂 OCR Voter Card Extractor (Folder Mode)")
    print("========================================")

    folder_path = input("📁 Enter the full path to the folder containing PDFs: ").strip()

    if not os.path.isdir(folder_path):
        print("❌ Error: The path provided is not a valid folder.")
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("⚠️ No PDF files found in the selected folder.")
        return

    print(f"📄 Found {len(pdf_files)} PDF(s) in folder. Starting OCR...\n")

    # Initialize progress state
    total_pdfs = len(pdf_files)
    progress_data = {}

    def log_callback(msg):
        print("📝", msg)

    def pdf_progress_callback(pdf_name):
        print(f"\n🔄 Starting: {pdf_name}")
        progress_data[pdf_name] = {"pages_done": 0, "total_pages": 0}

    def progress_callback(current_pdf, total_pdfs, pdf_name, pages_done, total_pages):
        progress_data[pdf_name]["pages_done"] = pages_done
        progress_data[pdf_name]["total_pages"] = total_pages

        status = f"📄 [{current_pdf}/{total_pdfs}] {pdf_name}: {pages_done}/{total_pages} page(s) processed"
        print(status, end="\r")

        if pages_done == total_pages:
            print(f"\n✅ Completed: {pdf_name}")

    try:
        entries = process_folder(
            folder_path,
            progress_callback=progress_callback,
            log_callback=log_callback,
            pdf_progress_callback=pdf_progress_callback
        )

        print("\n🎉 All PDFs processed successfully.")
        print(f"📦 Total entries extracted: {len(entries)}")

        # Optional: Save JSON
        import json
        json_output = os.path.join(folder_path, "output_combined.json")
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        print(f"🧾 JSON saved to: {json_output}")
        

    except Exception as e:
        print(f"\n❌ An error occurred during processing: {e}")

if __name__ == "__main__":
    run_cli_folder_ocr()
