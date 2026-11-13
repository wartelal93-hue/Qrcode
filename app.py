import os
import threading
import time
import requests
import qrcode
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

BASE_DIR = r"C:\PhotoboothSystem"
PHOTOS_FOLDER = os.path.join(BASE_DIR, "photos")
QRS_FOLDER = os.path.join(BASE_DIR, "qrs")

os.makedirs(PHOTOS_FOLDER, exist_ok=True)
os.makedirs(QRS_FOLDER, exist_ok=True)

RAILWAY_URL = ""
latest_qr_filename = ""
processed_prints = set()

class PhotoHandler(FileSystemEventHandler):
    on_created_callback = None

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            path_lower = event.src_path.lower()
            if 'originals' in path_lower or 'prints' in path_lower:
                try:
                    rel = os.path.relpath(event.src_path, PHOTOS_FOLDER)
                    parts = rel.split(os.sep)
                    if len(parts) >= 3:
                        event_name = parts[0]
                        event_dir = os.path.join(PHOTOS_FOLDER, event_name)
                        if self.on_created_callback:
                            self.on_created_callback(event_dir)
                except Exception as e:
                    print(f"Error path parsing: {e}")

def check_and_upload_session(event_dir):
    global latest_qr_filename, processed_prints, RAILWAY_URL
    if not RAILWAY_URL:
        return
    
    originals_dir = os.path.join(event_dir, 'Originals')
    prints_dir = os.path.join(event_dir, 'Prints')
    
    if not os.path.exists(originals_dir) or not os.path.exists(prints_dir):
        return
        
    orig_files = [f for f in os.listdir(originals_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    print_files = [f for f in os.listdir(prints_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if len(orig_files) >= 4 and len(print_files) >= 1:
        print_files.sort(key=lambda x: os.path.getmtime(os.path.join(prints_dir, x)))
        latest_print = print_files[-1]
        print_full_path = os.path.join(prints_dir, latest_print)
        
        if print_full_path in processed_prints:
            return
            
        processed_prints.add(print_full_path)
        
        print(f"\n[VALIDASI SUKSES] Mengunggah sesi ke Railway: {os.path.basename(event_dir)}")
        time.sleep(1.0) # Jeda stabilisasi file
        
        try:
            session_id = os.path.basename(event_dir)
            
            files_to_upload = {}
            files_to_upload['print'] = open(print_full_path, 'rb')
            
            orig_files.sort(key=lambda x: os.path.getmtime(os.path.join(originals_dir, x)))
            valid_orig = orig_files[-4:]
            
            for idx, orig_f in enumerate(valid_orig):
                orig_path = os.path.join(originals_dir, orig_f)
                files_to_upload[f'original_{idx}'] = open(orig_path, 'rb')
                
            data = {'session_id': session_id}
            
            response = requests.post(f"{RAILWAY_URL}/api/upload", files=files_to_upload, data=data)
            
            for f in files_to_upload.values():
                f.close()
                
            if response.status_code == 200:
                print("[SUKSES] Foto berhasil di-upload ke Railway!")
                
                photo_url = f"{RAILWAY_URL}/session/{session_id}"
                
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(photo_url)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                qr_filename = f"{session_id}_qr.png"
                qr_path = os.path.join(QRS_FOLDER, qr_filename)
                
                img.save(qr_path)
                latest_qr_filename = qr_path
                print(f"[SUKSES] QR Code dibuat dengan link cloud: {photo_url}")
            else:
                print(f"[ERROR UPLOAD] Server merespon: {response.text}")
        except Exception as e:
            print(f"[ERROR KONEKSI KE RAILWAY] {e}")

def start_main_app(url_input):
    global RAILWAY_URL
    RAILWAY_URL = url_input.strip().rstrip('/')
    if not RAILWAY_URL.startswith('http'):
        messagebox.showerror("Error", "URL Railway tidak valid! Harus diawali dengan https://")
        return
    
    # Tutup jendela setup, buka jendela utama display QR
    setup_root.destroy()
    launch_display_window()

def launch_display_window():
    root = tk.Tk()
    root.title("Photobooth Live QR Display (Railway Cloud)")
    root.geometry("600x700")
    root.configure(bg="#0f172a")
    
    title_label = tk.Label(root, text="SCAN UNTUK UNDUH FOTO", font=("Arial", 24, "bold"), fg="white", bg="#0f172a")
    title_label.pack(pady=30)
    
    frame = tk.Frame(root, bg="white", padx=20, pady=20, relief="raised")
    frame.pack(pady=10)
    
    img_label = tk.Label(frame, bg="white")
    img_label.pack()
    
    instruction_label = tk.Label(root, text="Arahkan kamera HP Anda ke QR Code di atas", font=("Arial", 14), fg="#94a3b8", bg="#0f172a")
    instruction_label.pack(pady=20)
    
    current_displayed_qr = ""

    def update_qr_display():
        nonlocal current_displayed_qr
        try:
            files = [f for f in os.listdir(QRS_FOLDER) if f.lower().endswith('.png')]
            if files:
                files.sort(key=lambda x: os.path.getmtime(os.path.join(QRS_FOLDER, x)), reverse=True)
                newest_qr_path = os.path.join(QRS_FOLDER, files[0])
                
                if newest_qr_path != current_displayed_qr:
                    current_displayed_qr = newest_qr_path
                    pil_img = Image.open(newest_qr_path)
                    pil_img = pil_img.resize((350, 350), Image.Resampling.LANCZOS)
                    tk_img = ImageTk.PhotoImage(pil_img)
                    img_label.config(image=tk_img)
                    img_label.image = tk_img
        except Exception as e:
            print(f"Error GUI update: {e}")
        
        root.after(1000, update_qr_display)

    root.after(1000, update_qr_display)
    
    def toggle_fullscreen(event=None):
        is_fs = root.attributes('-fullscreen')
        root.attributes('-fullscreen', not is_fs)
    root.bind("<F11>", toggle_fullscreen)
    root.bind("<Escape>", lambda e: root.attributes('-fullscreen', False))

    # Mulai pemantauan folder di background thread
    event_handler = PhotoHandler()
    event_handler.on_created_callback = check_and_upload_session
    
    observer = Observer()
    observer.schedule(event_handler, path=PHOTOS_FOLDER, recursive=True)
    observer.start()

    def on_closing():
        observer.stop()
        observer.join()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == '__main__':
    # Jendela Pertama: Kotak Masukkan URL Railway & Tombol Mulai
    setup_root = tk.Tk()
    setup_root.title("Konfigurasi Photobooth Railway")
    setup_root.geometry("480x260")
    setup_root.configure(bg="#0f172a")
    
    lbl_title = tk.Label(setup_root, text="Konfigurasi Photobooth Cloud", font=("Arial", 16, "bold"), fg="white", bg="#0f172a")
    lbl_title.pack(pady=20)
    
    lbl_url = tk.Label(setup_root, text="Paste URL Publik Railway Anda di sini:", font=("Arial", 11), fg="#cbd5e1", bg="#0f172a")
    lbl_url.pack(anchor="w", padx=40)
    
    url_entry = tk.Entry(setup_root, font=("Arial", 12), width=40)
    url_entry.pack(pady=8, padx=40)
    url_entry.insert(0, "https://")  # Format awal
    
    btn_start = tk.Button(setup_root, text="Mulai Sistem", font=("Arial", 12, "bold"), bg="#2563eb", fg="white", padx=25, pady=6, command=lambda: start_main_app(url_entry.get()))
    btn_start.pack(pady=12)
    
    setup_root.mainloop()