# pip install ultralytics opencv-python
import cv2, os, time, numpy as np
from ultralytics import YOLO

CAM_INDEX = 0
DESIRED_FULL_W, DESIRED_FULL_H = 3840, 2160
INFER_W, INFER_H = 640, 384   # multiple of 32
CONF_THRESH = 0.25
STABILITY_FRAMES = 1
CAPTURE_INTERVAL = 20          # seconds between captures
OUTPUT_DIR = "watch_folder"
MODEL_PATH = "yolov8n.pt"

os.makedirs(OUTPUT_DIR, exist_ok=True)
model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(CAM_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, DESIRED_FULL_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DESIRED_FULL_H)
time.sleep(0.3)

full_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
full_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Camera frame size: {full_w}x{full_h}")

last_bbox = None
stable_count = 0
save_idx = 0
last_capture_time = 0  # Track last save time

while True:
    ret, full_frame = cap.read()
    if not ret:
        print("Camera read failed")
        break

    # Run inference on a resized copy
    infer_frame = cv2.resize(full_frame, (INFER_W, INFER_H))
    results = model(infer_frame, imgsz=(INFER_W, INFER_H), conf=CONF_THRESH, verbose=False)
    r = results[0]

    if len(r.boxes) > 0:
        boxes = r.boxes
        confs = boxes.conf.cpu().numpy().flatten()
        idx = int(np.argmax(confs))
        xyxy = boxes.xyxy.cpu().numpy()[idx]
        conf = confs[idx]

        # Scale bbox to full res
        scale_x, scale_y = full_w / INFER_W, full_h / INFER_H
        x1, y1, x2, y2 = xyxy
        x1, y1, x2, y2 = int(x1 * scale_x), int(y1 * scale_y), int(x2 * scale_x), int(y2 * scale_y)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(full_w, x2), min(full_h, y2)

        # Stability check (simplified)
        if last_bbox is not None:
            lx1, ly1, lx2, ly2 = last_bbox
            inter_w = max(0, min(x2, lx2) - max(x1, lx1))
            inter_h = max(0, min(y2, ly2) - max(y1, ly1))
            inter_area = inter_w * inter_h
            this_area = (x2-x1)*(y2-y1)
            overlap = inter_area / this_area if this_area > 0 else 0
            if overlap > 0.5:
                stable_count += 1
            else:
                stable_count = 1
        else:
            stable_count = 1

        last_bbox = (x1, y1, x2, y2)

        # === CAPTURE with INTERVAL ===
        now = time.time()
        if stable_count >= STABILITY_FRAMES and (now - last_capture_time) >= CAPTURE_INTERVAL:
            crop = full_frame[y1:y2, x1:x2]
            if crop is not None and crop.size > 0:
                fname = os.path.join(OUTPUT_DIR, f"router_{save_idx:03d}.jpg")
                cv2.imwrite(fname, crop)
                print(f"[{time.strftime('%H:%M:%S')}] Saved: {fname} (interval ok)")
                save_idx += 1
                last_capture_time = now
                stable_count = 0

        # Display preview
        display = cv2.resize(full_frame, (1280, 720))
        cv2.rectangle(display, (int(x1/3), int(y1/3)), (int(x2/3), int(y2/3)), (0,255,0), 2)
        cv2.imshow("preview", display)
    else:
        stable_count = 0
        last_bbox = None
        cv2.imshow("preview", cv2.resize(full_frame, (1280, 720)))

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        # Manual snapshot
        fname = os.path.join(OUTPUT_DIR, f"manual_{int(time.time())}.jpg")
        cv2.imwrite(fname, full_frame)
        print(f"Manual saved: {fname}")

cap.release()
cv2.destroyAllWindows()