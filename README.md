# Router OCR Capture Web Application

A web-based interface for capturing router images using YOLO object detection with automatic OCR information extraction.

## Features

- 🎥 Live video streaming with real-time object detection
- 📸 Manual image capture via web button
- 🔍 Automatic OCR processing using Tesseract & EasyOCR
- 📊 Real-time extraction of router information:
  - WPA Key / WiFi Password
  - IP Address
  - SSID (Network Name)
  - MAC Address
  - Model Number
  - Serial Number
  - Username & Password
- ✨ Modern, responsive UI with beautiful data visualization
- 🎯 Real-time detection status
- 💾 Live capture counter

## Installation

1. **Install Tesseract OCR** (required for OCR functionality):
   
   **Windows:**
   - Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
   - Install and add to PATH
   
   **macOS:**
   ```bash
   brew install tesseract
   ```
   
   **Linux:**
   ```bash
   sudo apt-get install tesseract-ocr
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the web application:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. Click the **"Capture Image"** button when the router is detected (green badge shows "Router Detected")

4. The app will:
   - Save the cropped image to `watch_folder/router_XXX.jpg`
   - Automatically process the image with OCR
   - Display extracted information on the web UI in a beautiful grid layout

5. View the extracted router information including:
   - 🔐 WPA Key
   - 🌐 IP Address
   - 📡 SSID
   - 🔗 MAC Address
   - 📦 Model Number
   - 🏷️ Serial Number
   - 👤 Username
   - 🔑 Password

## Configuration

You can modify these settings in `app.py`:

- `CAM_INDEX`: Camera index (default: 0)
- `DESIRED_FULL_W`, `DESIRED_FULL_H`: Camera resolution (default: 3840x2160)
- `INFER_W`, `INFER_H`: Inference resolution (default: 640x384)
- `CONF_THRESH`: Confidence threshold for detection (default: 0.25)
- `OUTPUT_DIR`: Directory for saved images (default: "watch_folder")
- `MODEL_PATH`: YOLO model file (default: "yolov8n.pt")

## How It Works

1. The app captures frames from your camera
2. YOLO model detects objects in real-time
3. Detection box is drawn on the live feed
4. When you click "Capture", the app:
   - Saves the cropped region containing the detected object
   - Processes the image with OCR using both Tesseract and EasyOCR
   - Applies multiple preprocessing techniques for better accuracy
   - Extracts router information using regex patterns
   - Displays the results in a beautiful grid on the UI
5. The button is only enabled when an object is detected

## Differences from Original Script

- **Original (`livestream.py`)**: Automatically captures images every 20 seconds
- **New Web App (`app.py`)**: 
  - Manual capture via web UI button click
  - Automatic OCR processing with dual engines (Tesseract + EasyOCR)
  - Beautiful web interface with real-time data visualization
  - Extracts and displays 8+ router information fields
- Both use the same YOLO detection logic for object detection

## Troubleshooting

- **Camera issues**: If the camera doesn't initialize, try changing `CAM_INDEX` to 1 or 2
- **Detection issues**: If detection is poor, adjust `CONF_THRESH` (lower = more sensitive)
- **OCR issues**: 
  - Ensure Tesseract is installed and in your PATH
  - First run will download EasyOCR models (may take a few minutes)
  - For better results, ensure good lighting and focus on the router label
- **Model file**: Ensure `yolov8n.pt` model file is present in the project directory

