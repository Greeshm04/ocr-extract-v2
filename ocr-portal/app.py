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
from ocr_ultra_fast import process_single_image_ultra_fast

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
CONF_THRESH = 0.10  # Lowered from 0.25 for better detection of steady objects
OUTPUT_DIR = "watch_folder"
MODEL_PATH = "yolov8n.pt"
DEBUG_MODE = True  # Enable debug logging

# Global variables
os.makedirs(OUTPUT_DIR, exist_ok=True)
model = YOLO(MODEL_PATH)
cap = None
current_frame = None
current_bbox = None
frame_lock = threading.Lock()
save_idx = 0
frame_count = 0  # For debug logging

# OCR processing tracking
ocr_results = {}  # Store OCR results by filename
ocr_lock = threading.Lock()

def initialize_camera():
    global cap
    print("\n" + "="*60)
    print("🚀 Router OCR Information Extractor")
    print("="*60)
    print(f"📹 Camera Index: {CAM_INDEX}")
    print(f"🎯 Confidence Threshold: {CONF_THRESH} (lowered for better steady detection)")
    print(f"📊 Inference Resolution: {INFER_W}x{INFER_H}")
    print(f"🐛 Debug Mode: {'Enabled' if DEBUG_MODE else 'Disabled'}")
    print("="*60)
    
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, DESIRED_FULL_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DESIRED_FULL_H)
    
    # Improve camera settings for steady object detection
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Enable autofocus
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # Enable auto exposure
    
    time.sleep(0.5)  # Give camera time to adjust
    
    full_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    full_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"\n✅ Camera initialized successfully!")
    print(f"📐 Camera frame size: {full_w}x{full_h}")
    print("="*60 + "\n")

def process_frame():
    global current_frame, current_bbox, cap, frame_count
    
    frame_count += 1
    should_debug = DEBUG_MODE and (frame_count % 30 == 0)  # Debug every 30 frames
    
    ret, full_frame = cap.read()
    if not ret:
        return None, None
    
    # Run inference on a resized copy with lower confidence for better detection
    infer_frame = cv2.resize(full_frame, (INFER_W, INFER_H))
    results = model(infer_frame, imgsz=(INFER_W, INFER_H), conf=CONF_THRESH, verbose=False)
    r = results[0]
    
    bbox = None
    if len(r.boxes) > 0:
        boxes = r.boxes
        confs = boxes.conf.cpu().numpy().flatten()
        classes = boxes.cls.cpu().numpy().flatten() if hasattr(boxes, 'cls') else None
        
        # Debug: Print all detections (every 30 frames)
        if should_debug and len(confs) > 0:
            print(f"\n🔍 Frame {frame_count} - Detected {len(confs)} object(s):")
            for i, conf in enumerate(confs):
                cls_id = int(classes[i]) if classes is not None else -1
                cls_name = model.names[cls_id] if classes is not None and cls_id in model.names else "unknown"
                print(f"  #{i+1}: Class={cls_name} (id:{cls_id}), Confidence={conf:.3f}")
        
        # Get the highest confidence detection
        idx = int(np.argmax(confs))
        xyxy = boxes.xyxy.cpu().numpy()[idx]
        conf = confs[idx]
        
        if should_debug:
            print(f"✅ Using detection #{idx+1} with confidence {conf:.3f}")
        
        # Scale bbox to full res
        full_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        full_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        scale_x, scale_y = full_w / INFER_W, full_h / INFER_H
        x1, y1, x2, y2 = xyxy
        x1, y1, x2, y2 = int(x1 * scale_x), int(y1 * scale_y), int(x2 * scale_x), int(y2 * scale_y)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(full_w, x2), min(full_h, y2)
        bbox = (x1, y1, x2, y2, conf)
    else:
        if should_debug:
            print(f"❌ Frame {frame_count} - No objects detected")
    
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

def process_ocr_async(filename, filepath):
    """Process OCR in background thread"""
    try:
        print(f"\n{'='*60}")
        print(f"🔍 Starting OCR processing for {filename}...")
        print(f"   File path: {filepath}")
        print(f"   File exists: {os.path.exists(filepath)}")
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"   File size: {file_size} bytes")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        # Verify file exists
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Image file not found: {filepath}")
        
        # Use ULTRA-FAST OCR processing
        print(f"   Calling ULTRA-FAST OCR engine...")
        ocr_data = process_single_image_ultra_fast(filepath)
        
        elapsed = time.time() - start_time
        
        # Ensure we always have a valid result dictionary
        if ocr_data is None:
            print(f"   ⚠️  OCR returned None, creating empty result")
            ocr_data = {
                'wpa_key': None,
                'ip_address': None,
                'ssid': None,
                'mac_address': None,
                'model_number': None,
                'serial_number': None,
                'username': None,
                'password': None
            }
        
        print(f"\n✅ OCR completed for {filename} in {elapsed:.2f}s")
        
        # Debug: Print what was extracted
        found_fields = [k for k, v in ocr_data.items() if v is not None]
        print(f"   📊 Extracted {len(found_fields)} fields: {', '.join(found_fields) if found_fields else 'None'}")
        
        # Print actual values
        for field, value in ocr_data.items():
            if value:
                print(f"      • {field}: {value}")
        
        print(f"{'='*60}\n")
        
        # Store result
        with ocr_lock:
            ocr_results[filename] = {
                'status': 'completed',
                'data': ocr_data,
                'processing_time': elapsed
            }
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"\n❌ OCR error for {filename}: {error_msg}")
        print(f"   Full traceback:")
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        # Store error with empty data so frontend can still display something
        with ocr_lock:
            ocr_results[filename] = {
                'status': 'error',
                'error': error_msg,
                'data': {
                    'wpa_key': None,
                    'ip_address': None,
                    'ssid': None,
                    'mac_address': None,
                    'model_number': None,
                    'serial_number': None,
                    'username': None,
                    'password': None
                }
            }

@app.route('/capture', methods=['POST'])
def capture():
    global save_idx
    
    with frame_lock:
        if current_bbox is not None and current_frame is not None:
            x1, y1, x2, y2, conf = current_bbox
            crop = current_frame[y1:y2, x1:x2]
            
            if crop is not None and crop.size > 0:
                filename = f"router_{save_idx:03d}.jpg"
                filepath = os.path.join(OUTPUT_DIR, filename)
                cv2.imwrite(filepath, crop)
                print(f"[{time.strftime('%H:%M:%S')}] Saved: {filepath}")
                
                # Initialize OCR status
                with ocr_lock:
                    ocr_results[filename] = {'status': 'processing'}
                
                # Start OCR in background thread
                ocr_thread = threading.Thread(
                    target=process_ocr_async, 
                    args=(filename, filepath),
                    daemon=True
                )
                ocr_thread.start()
                
                save_idx += 1
                
                # Return immediately without waiting for OCR
                return jsonify({
                    'status': 'success', 
                    'message': f'Image captured: {filename}',
                    'filename': filename,
                    'ocr_status': 'processing'
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

@app.route('/ocr_result/<filename>', methods=['GET'])
def get_ocr_result(filename):
    """Get OCR processing result for a specific file"""
    with ocr_lock:
        if filename in ocr_results:
            result = ocr_results[filename]
            if result['status'] == 'completed':
                return jsonify({
                    'status': 'completed',
                    'ocr_data': result['data'],
                    'processing_time': result.get('processing_time', 0)
                })
            elif result['status'] == 'processing':
                return jsonify({'status': 'processing'})
            else:  # error - but still return data if available
                return jsonify({
                    'status': 'completed',  # Mark as completed so frontend shows results
                    'ocr_data': result.get('data', {}),
                    'processing_time': result.get('processing_time', 0),
                    'warning': f"OCR had errors: {result.get('error', 'Unknown error')}"
                })
        else:
            return jsonify({'status': 'not_found'}), 404

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
    # Initialize ULTRA-FAST OCR engine at startup for faster first capture
    print("\n🔄 Pre-initializing ULTRA-FAST OCR engine...")
    from ocr_ultra_fast import UltraFastRouterOCR
    _ = UltraFastRouterOCR()  # Initialize singleton
    print("✅ ULTRA-FAST OCR engine ready!\n")
    
    initialize_camera()
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)

