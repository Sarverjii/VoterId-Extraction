import threading
import json
import os
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, scrolledtext, messagebox
from tkinter import ttk as tkttk  # For PanedWindow
from main4 import process_pdf, process_folder


class OCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🪪 OCR Voter Card Extractor")
        self.root.geometry("1080x720")
        self.root.minsize(900, 600)

        self.page_bars = []
        self.status_label = None
        self.selected_path = ""
        self.is_folder = False

        self.setup_ui()

    def setup_ui(self):
        # === Top Bar: File/Folder selection and status ===
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", pady=10, padx=10)

        # Path display
        self.path_label = ttk.Label(
            top_frame, text="📄 No File/Folder Selected", font=("Segoe UI", 10), foreground="#666"
        )
        self.path_label.pack(side="left", padx=(0, 10))

        # Browse buttons
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side="left")

        ttk.Button(button_frame, text="📂 Browse PDF", bootstyle="primary-outline", command=self.browse_pdf).pack(side="left", padx=(0, 5))
        ttk.Button(button_frame, text="📁 Browse Folder", bootstyle="info-outline", command=self.browse_folder).pack(side="left", padx=(5, 0))

        # Start button
        self.start_btn = ttk.Button(top_frame, text="▶️ Start OCR", state=DISABLED, bootstyle="success", command=self.start_ocr)
        self.start_btn.pack(side="left", padx=10)

        # Status label
        self.status_label = ttk.Label(top_frame, text="", font=("Segoe UI", 10, "bold"))
        self.status_label.pack(side="right")

        # === Main Pane: Split Progress & Output ===
        main_pane = tkttk.PanedWindow(self.root, orient="vertical")
        main_pane.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # === Scrollable Progress Section ===
        progress_wrapper = ttk.Frame(main_pane)
        main_pane.add(progress_wrapper, weight=3)

        canvas = ttk.Canvas(progress_wrapper)
        scrollbar = ttk.Scrollbar(progress_wrapper, orient="vertical", command=canvas.yview)
        self.progress_frame = ttk.Frame(canvas)

        self.progress_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.progress_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # === Bottom Notebook for Logs and JSON Preview ===
        output_tabs = ttk.Notebook(main_pane, bootstyle="secondary")
        main_pane.add(output_tabs, weight=1)

        self.log_text = scrolledtext.ScrolledText(output_tabs, height=10)
        self.json_text = scrolledtext.ScrolledText(output_tabs, height=10)

        output_tabs.add(self.log_text, text="📜 Logs")
        output_tabs.add(self.json_text, text="🧾 JSON Preview")

    def browse_pdf(self):
        pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if pdf_path:
            self.selected_path = pdf_path
            self.is_folder = False
            self.start_btn.config(state=NORMAL)
            short_path = pdf_path if len(pdf_path) < 80 else "..." + pdf_path[-77:]
            self.path_label.config(text=f"📄 PDF: {short_path}")
            self.status_label.config(text="")

    def browse_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            # Check if folder contains PDF files
            pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
            if not pdf_files:
                messagebox.showwarning("No PDFs Found", "The selected folder contains no PDF files.")
                return
            
            self.selected_path = folder_path
            self.is_folder = True
            self.start_btn.config(state=NORMAL)
            short_path = folder_path if len(folder_path) < 70 else "..." + folder_path[-67:]
            self.path_label.config(text=f"📁 Folder: {short_path} ({len(pdf_files)} PDFs)")
            self.status_label.config(text="")

    def start_ocr(self):
        self.clear_previous()
        self.start_btn.config(state=DISABLED)
        self.status_label.config(text="🔄 Starting...", foreground="blue")
        
        if self.is_folder:
            self.log("🔄 Starting folder OCR...")
        else:
            self.log("🔄 Starting PDF OCR...")

        threading.Thread(target=self.run_ocr, daemon=True).start()

    def run_ocr(self):
        try:
            if self.is_folder:
                # Process folder - show one progress bar per PDF
                entries = process_folder(
                    self.selected_path,
                    progress_callback=self.update_folder_progress,
                    log_callback=self.log,
                    pdf_progress_callback=self.create_pdf_progress
                )
            else:
                # Process single PDF - show one progress bar per page
                from PyPDF2 import PdfReader
                reader = PdfReader(self.selected_path)
                total_pages = len(reader.pages) - 3  # Skip first two pages

                # Create progress bars for each page
                for i in range(total_pages):
                    self.create_page_progress(i + 3, os.path.basename(self.selected_path))

                entries, _ = process_pdf(
                    self.selected_path,
                    progress_callback=self.update_single_pdf_progress,
                    log_callback=self.log
                )

            # Display results in JSON preview
            self.json_text.delete("1.0", "end")
            self.json_text.insert("end", json.dumps(entries, indent=2, ensure_ascii=False))

            self.status_label.config(text="✅ OCR Complete", foreground="green")
            self.log("✅ OCR Completed Successfully")

        except Exception as e:
            self.log(f"❌ Error: {e}")
            self.status_label.config(text="❌ Error Occurred", foreground="red")
        finally:
            self.start_btn.config(state=NORMAL)

    def update_single_pdf_progress(self, global_done, global_total, page_index, local_box_num, total_boxes):
        """Update progress for single PDF processing - one bar per page"""
        if 0 <= page_index < len(self.page_bars):
            bar, label = self.page_bars[page_index]
            percent = (local_box_num / total_boxes) * 100
            bar["value"] = percent

            page_display = f"Page {page_index + 3}"

            if local_box_num == total_boxes:
                bar.configure(bootstyle="success-striped")
                label.config(text=f"✅ {page_display} Complete")
            else:
                label.config(text=f"📄 {page_display} — {local_box_num}/{total_boxes}")

    def create_pdf_progress(self, pdf_name):
        """Create progress bar for a PDF file (used in folder processing)"""
        # Debug: Check if we're creating duplicate progress bars
        existing_names = [label.cget("text") for _, label in self.page_bars]
        if f"📄 {pdf_name}" in existing_names:
            self.log(f"⚠️ Warning: Progress bar for {pdf_name} already exists!")
            return
        
        frame = ttk.Frame(self.progress_frame)
        frame.pack(fill="x", pady=5)

        label = ttk.Label(frame, text=f"📄 {pdf_name}", font=("Segoe UI", 10, "bold"))
        label.pack(side="left", padx=10)

        bar = ttk.Progressbar(frame, length=600, mode="determinate", bootstyle="info-striped")
        bar.pack(side="left", fill="x", expand=True, padx=5)

        self.page_bars.append((bar, label))
        self.log(f"✅ Created progress bar for: {pdf_name}")

    def update_folder_progress(self, current_pdf, total_pdfs, pdf_name, pages_done, total_pages):
        """Update progress for folder processing - one bar per PDF"""
        pdf_index = current_pdf - 1  # Convert to 0-based index
        
        if 0 <= pdf_index < len(self.page_bars):
            bar, label = self.page_bars[pdf_index]
            
            if total_pages > 0:
                percent = (pages_done / total_pages) * 100
                bar["value"] = percent
                
                if pages_done == total_pages:
                    bar.configure(bootstyle="success-striped")
                    label.config(text=f"✅ {pdf_name} Complete")
                else:
                    label.config(text=f"📄 {pdf_name} — {pages_done}/{total_pages} pages")
            else:
                label.config(text=f"📄 {pdf_name} — Processing...")

    def create_page_progress(self, page_num, pdf_name):
        """Create progress bar for a page (used in single PDF processing)"""
        frame = ttk.Frame(self.progress_frame)
        frame.pack(fill="x", pady=5)

        page_display = f"{pdf_name} - Page {page_num}"
        label = ttk.Label(frame, text=f"📄 {page_display}", font=("Segoe UI", 10, "bold"))
        label.pack(side="left", padx=10)

        bar = ttk.Progressbar(frame, length=600, mode="determinate", bootstyle="info-striped")
        bar.pack(side="left", fill="x", expand=True, padx=5)

        self.page_bars.append((bar, label))

    def log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def clear_previous(self):
        for widget in self.progress_frame.winfo_children():
            widget.destroy()
        self.page_bars.clear()
        self.log_text.delete("1.0", "end")
        self.json_text.delete("1.0", "end")


if __name__ == "__main__":
    root = ttk.Window(themename="flatly")  # morph/superhero/cyborg/lux/litera
    app = OCRApp(root)
    root.mainloop()