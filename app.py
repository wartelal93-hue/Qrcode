import os
from flask import Flask, render_template_string, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def home():
    return "Photobooth Cloud Server is Running!"

@app.route('/api/upload', methods=['POST'])
def upload_session():
    try:
        session_id = request.form.get('session_id', 'default')
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        originals_dir = os.path.join(session_dir, 'Originals')
        prints_dir = os.path.join(session_dir, 'Prints')
        
        os.makedirs(originals_dir, exist_ok=True)
        os.makedirs(prints_dir, exist_ok=True)
        
        if 'print' in request.files:
            file = request.files['print']
            filename = secure_filename(file.filename)
            file.save(os.path.join(prints_dir, filename))
            
        for key in request.files:
            if key.startswith('original_'):
                file = request.files[key]
                filename = secure_filename(file.filename)
                file.save(os.path.join(originals_dir, filename))
                
        return jsonify({"status": "success", "session_id": session_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/session/<session_id>')
def view_session(session_id):
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    originals_dir = os.path.join(session_dir, 'Originals')
    prints_dir = os.path.join(session_dir, 'Prints')
    
    if not os.path.exists(session_dir):
        return "Sesi foto tidak ditemukan.", 404
        
    print_files = os.listdir(prints_dir) if os.path.exists(prints_dir) else []
    
    # Filter ketat: Hanya ambil 4 foto original terbaru untuk sesi ini
    orig_files = []
    if os.path.exists(originals_dir):
        all_orig = []
        for f in os.listdir(originals_dir):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                f_path = os.path.join(originals_dir, f)
                f_mtime = os.path.getmtime(f_path)
                all_orig.append((f, f_mtime))
        # Urutkan berdasarkan waktu dan ambil 4 terakhir saja
        all_orig.sort(key=lambda x: x[1])
        orig_files = [item[0] for item in all_orig[-4:]]
    
    print_url = f"/file/{session_id}/Prints/{print_files[0]}" if print_files else ""
    original_urls = [f"/file/{session_id}/Originals/{f}" for f in orig_files]
    
    html_template = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Unduh Foto Photobooth Anda</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background: #f8fafc; padding: 20px; color: #334155; margin: 0; }
            .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
            h2 { color: #0f172a; margin-top: 0; }
            .main-photo { max-width: 100%; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin-bottom: 20px; }
            .btn { display: inline-block; background: #2563eb; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; margin-bottom: 30px; box-shadow: 0 4px 10px rgba(37,99,235,0.3); }
            .btn:hover { background: #1d4ed8; }
            .originals-section { text-align: left; border-top: 2px solid #f1f5f9; padding-top: 20px; }
            .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 15px; }
            .grid img { width: 100%; border-radius: 8px; border: 2px solid #e2e8f0; }
            p.instruction { color: #64748b; font-size: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Hasil Foto Photobooth Anda 🎉</h2>
            <p class="instruction">Tekan dan tahan foto di bawah untuk menyimpan ke HP Anda.</p>
            {% if print_url %}
            <img class="main-photo" src="{{ print_url }}" alt="Foto Print">
            <br>
            <a class="btn" href="{{ print_url }}" download>📥 Unduh Foto Hasil (Frame)</a>
            {% endif %}
            
            {% if original_urls %}
            <div class="originals-section">
                <h3>Foto Satuan (Originals)</h3>
                <p class="instruction" style="margin-top:0;">Berikut adalah 4 foto mentah sesi Anda:</p>
                <div class="grid">
                    {% for url in original_urls %}
                        <div>
                            <img src="{{ url }}" alt="Foto Original">
                            <a href="{{ url }}" download style="display:block; text-align:center; font-size:13px; margin-top:4px; color:#2563eb; text-decoration:none; font-weight:bold;">Download Asli</a>
                        </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, print_url=print_url, original_urls=original_urls)

@app.route('/file/<session_id>/<folder>/<filename>')
def serve_file(session_id, folder, filename):
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], session_id, folder)
    return send_from_directory(folder_path, filename)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
