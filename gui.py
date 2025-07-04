import threading
import json
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, scrolledtext
from tkinter import ttk as tkttk  # For PanedWindow
from main2 import process_pdf


class OCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🪪 OCR Voter Card Extractor")
        self.root.geometry("1080x720")
        self.root.minsize(900, 600)

        self.page_bars = []
        self.status_label = None
        self.pdf_path = ""

        self.setup_ui()

    def setup_ui(self):
        # === Top Bar: File selection and status ===
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", pady=10, padx=10)

        self.pdf_path_label = ttk.Label(
            top_frame, text="📄 No PDF Selected", font=("Segoe UI", 10), foreground="#666"
        )
        self.pdf_path_label.pack(side="left", padx=(0, 10))

        ttk.Button(top_frame, text="📂 Browse PDF", bootstyle="primary-outline", command=self.browse_pdf).pack(side="left")
        self.start_btn = ttk.Button(top_frame, text="▶️ Start OCR", state=DISABLED, bootstyle="success", command=self.start_ocr)
        self.start_btn.pack(side="left", padx=10)

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
        self.pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if self.pdf_path:
            self.start_btn.config(state=NORMAL)
            short_path = self.pdf_path if len(self.pdf_path) < 90 else "..." + self.pdf_path[-87:]
            self.pdf_path_label.config(text=f"📄 {short_path}")
            self.status_label.config(text="")

    def start_ocr(self):
        self.clear_previous()
        self.start_btn.config(state=DISABLED)
        self.status_label.config(text="🔄 Starting...", foreground="blue")
        self.log("🔄 Starting OCR...")

        threading.Thread(target=self.run_ocr, daemon=True).start()

    def run_ocr(self):
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(self.pdf_path)
            total_pages = len(reader.pages) - 3  # Skip first two pages

            for i in range(total_pages):
                self.create_page_progress(i + 3)

            entries, _ = process_pdf(
                self.pdf_path,
                progress_callback=self.update_progress,
                log_callback=self.log
            )

            self.json_text.delete("1.0", "end")
            self.json_text.insert("end", json.dumps(entries, indent=2, ensure_ascii=False))

            self.status_label.config(text="✅ OCR Complete", foreground="green")
            self.log("✅ OCR Completed Successfully")

        except Exception as e:
            self.log(f"❌ Error: {e}")
            self.status_label.config(text="❌ Error Occurred", foreground="red")
        finally:
            self.start_btn.config(state=NORMAL)

    def update_progress(self, global_done, global_total, page_index, local_box_num, total_boxes):
        if 0 <= page_index < len(self.page_bars):
            bar, label = self.page_bars[page_index]
            percent = (local_box_num / total_boxes) * 100
            bar["value"] = percent

            if local_box_num == total_boxes:
                bar.configure(bootstyle="success-striped")
                label.config(text=f"✅ Page {page_index + 3} Complete")
            else:
                label.config(text=f"📄 Page {page_index + 3} — {local_box_num}/{total_boxes}")

    def create_page_progress(self, page_num):
        frame = ttk.Frame(self.progress_frame)
        frame.pack(fill="x", pady=5)

        label = ttk.Label(frame, text=f"📄 Page {page_num}", font=("Segoe UI", 10, "bold"))
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
