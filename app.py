import os
import sqlite3
import json
import uuid
import numpy as np
import cv2
from io import BytesIO
from datetime import datetime
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory, send_file, render_template
from ultralytics import YOLO
import pydicom
from pydicom.dataset import Dataset, FileDataset

app = Flask(__name__, template_folder='templates', static_folder='static')

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['RESULT_FOLDER'] = 'results/'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
DB_FILE = 'fractures.db'
MODEL_PATH = 'best.pt'
ALLOWED_EXTENSIONS = {'png', 'dcm', 'dicom'}

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

# Load Model
try:
    model = YOLO(MODEL_PATH)
except Exception as e:
    print(f"Warning: Could not load model {MODEL_PATH}: {e}")
    model = None

# Class configurations
CLASS_NAMES = [
    "Comminuted",
    "Greenstick",
    "Linear",
    "Oblique Displaced",
    "Oblique",
    "Segmental",
    "Spiral",
    "Transverse Displaced",
    "Transverse",
    "Healthy"
]

CLASS_NAMES_VI = {
    "Comminuted": "Gãy vụn",
    "Greenstick": "Gãy cành tươi",
    "Linear": "Gãy đường thẳng",
    "Oblique Displaced": "Gãy chéo di lệch",
    "Oblique": "Gãy chéo",
    "Segmental": "Gãy phân đoạn",
    "Spiral": "Gãy xoắn",
    "Transverse Displaced": "Gãy ngang di lệch",
    "Transverse": "Gãy ngang",
    "Healthy": "Khỏe mạnh"
}

# Hex to BGR
def hex_to_bgr(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (4, 2, 0))

CLASS_COLORS_HEX = {
    "Comminuted": "#FF4444",
    "Greenstick": "#44FF44",
    "Linear": "#4444FF",
    "Oblique Displaced": "#FF8C00",
    "Oblique": "#FFD700",
    "Segmental": "#FF69B4",
    "Spiral": "#00CED1",
    "Transverse Displaced": "#9370DB",
    "Transverse": "#20B2AA",
    "Healthy": "#00FF7F"
}

CLASS_COLORS = {name: hex_to_bgr(hex_code) for name, hex_code in CLASS_COLORS_HEX.items()}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            upload_path TEXT,
            result_path TEXT,
            original_format TEXT,
            num_detections INTEGER,
            detections_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def apply_dicom_windowing(ds, img_array):
    if 'WindowCenter' in ds and 'WindowWidth' in ds:
        center = ds.WindowCenter
        width = ds.WindowWidth
        if isinstance(center, pydicom.multival.MultiValue):
            center = float(center[0])
        else:
            center = float(center)
        if isinstance(width, pydicom.multival.MultiValue):
            width = float(width[0])
        else:
            width = float(width)
        
        vmin = center - width / 2.0
        vmax = center + width / 2.0
        img_array = np.clip(img_array, vmin, vmax)
        img_array = ((img_array - vmin) / (vmax - vmin) * 255.0).astype(np.uint8)
    else:
        # Auto-window
        p1 = np.percentile(img_array, 1)
        p99 = np.percentile(img_array, 99)
        img_array = np.clip(img_array, p1, p99)
        img_array = ((img_array - p1) / (p99 - p1) * 255.0).astype(np.uint8)
    return img_array

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        try:
            ext = file.filename.rsplit('.', 1)[1].lower()
            original_format = 'dicom' if ext in ['dcm', 'dicom'] else 'png'
            unique_id = str(uuid.uuid4())
            upload_filename = f"{unique_id}.{ext}"
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], upload_filename)
            file.save(upload_path)
            
            # Read image
            if original_format == 'dicom':
                ds = pydicom.dcmread(upload_path)
                img_array = ds.pixel_array.astype(float)
                
                if 'RescaleSlope' in ds and 'RescaleIntercept' in ds:
                    img_array = img_array * float(ds.RescaleSlope) + float(ds.RescaleIntercept)
                
                img_array = apply_dicom_windowing(ds, img_array)
                
                if ds.PhotometricInterpretation == 'MONOCHROME1':
                    img_array = np.amax(img_array) - img_array
                    
                image = Image.fromarray(img_array).convert('RGB')
            else:
                image = Image.open(upload_path).convert('RGB')
            
            # Convert to cv2 image for drawing
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Save original preview (before drawing bboxes)
            original_preview_filename = f"original_{unique_id}.png"
            original_preview_path = os.path.join(app.config['RESULT_FOLDER'], original_preview_filename)
            cv2.imwrite(original_preview_path, cv_image.copy())
            
            # Inference
            if model:
                results = model.predict(image, conf=0.25)
            else:
                results = []
                
            detections = []
            if results:
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        class_name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else "Unknown"
                        class_name_vi = CLASS_NAMES_VI.get(class_name, class_name)
                        
                        detections.append({
                            'class_name': class_name,
                            'class_name_vi': class_name_vi,
                            'confidence': conf,
                            'bbox': [x1, y1, x2, y2]
                        })
                        
                        # Draw bbox
                        color = CLASS_COLORS.get(class_name, (0, 255, 0))
                        cv2.rectangle(cv_image, (x1, y1), (x2, y2), color, 2)
                        
                        # Draw label
                        label = f"{class_name_vi} {conf:.2f}"
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = 0.6
                        thickness = 1
                        (w, h), _ = cv2.getTextSize(label, font, font_scale, thickness)
                        cv2.rectangle(cv_image, (x1, y1 - h - 10), (x1 + w, y1), color, -1)
                        cv2.putText(cv_image, label, (x1, y1 - 5), font, font_scale, (255, 255, 255), thickness)
            
            result_filename = f"result_{unique_id}.png"
            result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
            cv2.imwrite(result_path, cv_image)
            
            # Save to DB
            detections_json = json.dumps(detections)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''
                INSERT INTO predictions (filename, upload_path, result_path, original_format, num_detections, detections_json)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (file.filename, upload_path, result_path, original_format, len(detections), detections_json))
            pred_id = c.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'prediction': {
                    'id': pred_id,
                    'filename': file.filename,
                    'num_detections': len(detections),
                    'detections': detections,
                    'original_image_url': f"/results/{original_preview_filename}",
                    'result_image_url': f"/results/{result_filename}",
                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({'success': False, 'error': 'Invalid file type'}), 400

@app.route('/results/<path:filename>')
def serve_result(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

@app.route('/api/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM predictions ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            'id': row['id'],
            'filename': row['filename'],
            'num_detections': row['num_detections'],
            'detections': json.loads(row['detections_json']),
            'result_image_url': f"/results/{os.path.basename(row['result_path'])}",
            'original_format': row['original_format'],
            'created_at': row['created_at']
        })
    return jsonify(history)

@app.route('/api/download/<int:pred_id>')
def download(pred_id):
    fmt = request.args.get('format', 'png')
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM predictions WHERE id = ?', (pred_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'success': False, 'error': 'Prediction not found'}), 404
        
    result_path = row['result_path']
    if not os.path.exists(result_path):
        return jsonify({'success': False, 'error': 'Result file not found'}), 404
        
    if fmt == 'png':
        return send_file(result_path, as_attachment=True, download_name=f"result_{row['filename']}.png")
    elif fmt == 'dicom':
        try:
            # Create a secondary capture DICOM
            result_img = cv2.imread(result_path)
            # Convert to grayscale for standard secondary capture or keep RGB. 
            # We will convert to MONOCHROME2 grayscale as requested by instructions.
            gray_img = cv2.cvtColor(result_img, cv2.COLOR_BGR2GRAY)
            
            # Create a new dataset
            file_meta = pydicom.dataset.FileMetaDataset()
            file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7' # Secondary Capture Image Storage
            file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
            file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
            
            ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
            ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
            ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
            ds.PatientName = "Anonymous^Patient"
            ds.PatientID = "123456"
            ds.StudyDate = datetime.now().strftime('%Y%m%d')
            ds.StudyTime = datetime.now().strftime('%H%M%S')
            ds.Modality = "OT"
            
            # If original was DICOM, copy some metadata
            if row['original_format'] == 'dicom' and os.path.exists(row['upload_path']):
                try:
                    orig_ds = pydicom.dcmread(row['upload_path'])
                    for tag in ['PatientName', 'PatientID', 'PatientBirthDate', 'PatientSex', 'StudyDate', 'StudyTime', 'StudyInstanceUID', 'SeriesInstanceUID']:
                        if tag in orig_ds:
                            setattr(ds, tag, getattr(orig_ds, tag))
                except Exception as e:
                    print("Could not read original dicom for metadata:", e)
                    
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.PixelRepresentation = 0
            ds.HighBit = 7
            ds.BitsStored = 8
            ds.BitsAllocated = 8
            ds.Rows, ds.Columns = gray_img.shape
            ds.PixelData = gray_img.tobytes()
            
            temp_dicom_path = os.path.join(app.config['RESULT_FOLDER'], f"temp_{uuid.uuid4()}.dcm")
            ds.save_as(temp_dicom_path, write_like_original=False)
            
            return send_file(temp_dicom_path, as_attachment=True, download_name=f"result_{row['filename']}.dcm")
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'Invalid format requested'}), 400

@app.route('/api/delete/<int:pred_id>', methods=['DELETE'])
def delete_pred(pred_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM predictions WHERE id = ?', (pred_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Not found'}), 404
        
    try:
        if os.path.exists(row[2]):  # upload_path
            os.remove(row[2])
        if os.path.exists(row[3]):  # result_path
            os.remove(row[3])
    except Exception as e:
        print("Error deleting files:", e)
        
    c.execute('DELETE FROM predictions WHERE id = ?', (pred_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
