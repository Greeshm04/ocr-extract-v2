from flask import Flask, render_template, Response, jsonify, request
import cv2
import os
import time
import numpy as np
import torch
import torch.serialization
from ultralytics import YOLO
import threading
import json
from ocrV5 import process_single_image

# Fix for PyTorch 2.6+ weights_only security feature
try:
    from ultralytics.nn.tasks import DetectionModel
    torch.serialization.add_safe_globals([DetectionModel])
except:
    pass

app = Flask(__name__)

# Configuration
CAM_INDEX = 0
DESIRED_FULL_W, DESIRED_FULL_H = 3840, 2160
INFER_W, INFER_H = 640, 384   # multiple of 32
CONF_THRESH = 0.25
OUTPUT_DIR = "watch_folder"
MODEL_PATH = "yolov8n.pt"

# Global variables
os.makedirs(OUTPUT_DIR, exist_ok=True)
model = YOLO(MODEL_PATH)
cap = None
current_frame = None
current_bbox = None
frame_lock = threading.Lock()
save_idx = 0

def initialize_camera():
    global cap
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, DESIRED_FULL_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DESIRED_FULL_H)
    time.sleep(0.3)
    full_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    full_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera frame size: {full_w}x{full_h}")

def process_frame():
    global current_frame, current_bbox, cap
    
    ret, full_frame = cap.read()
    if not ret:
        return None, None
    
    # Run inference on a resized copy
    infer_frame = cv2.resize(full_frame, (INFER_W, INFER_H))
    results = model(infer_frame, imgsz=(INFER_W, INFER_H), conf=CONF_THRESH, verbose=False)
    r = results[0]
    
    bbox = None
    if len(r.boxes) > 0:
        boxes = r.boxes
        confs = boxes.conf.cpu().numpy().flatten()
        idx = int(np.argmax(confs))
        xyxy = boxes.xyxy.cpu().numpy()[idx]
        conf = confs[idx]
        
        # Scale bbox to full res
        full_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        full_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        scale_x, scale_y = full_w / INFER_W, full_h / INFER_H
        x1, y1, x2, y2 = xyxy
        x1, y1, x2, y2 = int(x1 * scale_x), int(y1 * scale_y), int(x2 * scale_x), int(y2 * scale_y)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(full_w, x2), min(full_h, y2)
        bbox = (x1, y1, x2, y2, conf)
    
    return full_frame, bbox

def generate_frames():
    global current_frame, current_bbox, frame_lock
    
    while True:
        with frame_lock:
            full_frame, bbox = process_frame()
            
            if full_frame is None:
                break
            
            current_frame = full_frame.copy()
            current_bbox = bbox
            
            # Create display frame
            display = cv2.resize(full_frame, (1280, 720))
            
            # Draw bbox on display
            if bbox is not None:
                x1, y1, x2, y2, conf = bbox
                # Scale bbox to display resolution
                dx1, dy1 = int(x1 * 1280 / full_frame.shape[1]), int(y1 * 720 / full_frame.shape[0])
                dx2, dy2 = int(x2 * 1280 / full_frame.shape[1]), int(y2 * 720 / full_frame.shape[0])
                cv2.rectangle(display, (dx1, dy1), (dx2, dy2), (0, 255, 0), 2)
                cv2.putText(display, f"Conf: {conf:.2f}", (dx1, dy1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', display)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    global save_idx
    
    with frame_lock:
        if current_bbox is not None and current_frame is not None:
            x1, y1, x2, y2, conf = current_bbox
            crop = current_frame[y1:y2, x1:x2]
            
            if crop is not None and crop.size > 0:
                fname = os.path.join(OUTPUT_DIR, f"router_{save_idx:03d}.jpg")
                cv2.imwrite(fname, crop)
                print(f"[{time.strftime('%H:%M:%S')}] Saved: {fname}")
                
                # Process with OCR
                print("🔍 Processing image with OCR...")
                ocr_data = process_single_image(fname, output_format='dict')
                
                save_idx += 1
                
                return jsonify({
                    'status': 'success', 
                    'message': f'Image captured: router_{save_idx-1:03d}.jpg',
                    'filename': f'router_{save_idx-1:03d}.jpg',
                    'ocr_data': ocr_data
                })
        else:
            return jsonify({'status': 'error', 'message': 'No router detected'}), 400

@app.route('/status')
def status():
    with frame_lock:
        return jsonify({
            'detected': current_bbox is not None,
            'saved_count': save_idx
        })

@app.route('/save_ocr', methods=['POST'])
def save_ocr():
    try:
        data = request.get_json()
        filename = data.get('filename')
        ocr_data = data.get('ocr_data')
        
        if not filename or not ocr_data:
            return jsonify({'status': 'error', 'message': 'Missing filename or OCR data'}), 400
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(OUTPUT_DIR, 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate JSON filename (same as image but with .json extension)
        json_filename = os.path.splitext(filename)[0] + '.json'
        json_path = os.path.join(output_dir, json_filename)
        
        # Save OCR data as JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(ocr_data, f, indent=4, ensure_ascii=False)
        
        print(f"[{time.strftime('%H:%M:%S')}] Saved JSON: {json_path}")
        
        return jsonify({
            'status': 'success',
            'message': f'Data saved successfully: {json_filename}'
        })
        
    except Exception as e:
        print(f"Error saving OCR data: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Failed to save: {str(e)}'}), 500

if __name__ == '__main__':
    initialize_camera()
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)

