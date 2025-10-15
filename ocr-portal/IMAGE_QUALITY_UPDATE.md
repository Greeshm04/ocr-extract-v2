# Image Quality Update for OCR

## Changes Made

### ✅ PNG Format (Lossless)
- **Before**: Images saved as JPG (lossy compression)
- **After**: Images saved as PNG (lossless compression)
- **Benefit**: No quality loss, perfect for OCR

### ✅ Maximum Quality Settings
- PNG compression level set to `0` (no compression = highest quality)
- File format: `router_XXX.png` instead of `router_XXX.jpg`

### ✅ 4K Resolution Capture
- Camera already configured for **3840x2160** (4K) resolution
- Full resolution frames are captured and cropped
- Display is downscaled to 1280x720 (for web view only)
- **Saved images**: Full 4K resolution crop

## Technical Details

### Image Saving Code
```python
# PNG with maximum quality (compression level 0)
cv2.imwrite(fname, crop, [cv2.IMWRITE_PNG_COMPRESSION, 0])
```

### Resolution Flow
1. **Camera captures**: 3840x2160 (4K) - highest quality
2. **YOLO inference**: 640x384 (downscaled for speed)
3. **Bounding box**: Calculated on full 4K frame
4. **Saved crop**: Full 4K resolution in PNG format
5. **Web display**: Downscaled to 1280x720 (for browser performance)

## Benefits for OCR

1. **Lossless Format**: PNG preserves all pixel data (no JPEG artifacts)
2. **High Resolution**: 4K capture ensures text is sharp and clear
3. **Better Accuracy**: OCR engines work much better with high-quality images
4. **No Compression Artifacts**: Eliminates blur and noise from JPEG compression

## File Size Considerations

- PNG files will be **larger** than JPG (typically 2-5x)
- Trade-off: Storage space vs OCR accuracy
- Recommendation: Archive/delete processed images after extraction

## Restart Required

The Flask app will auto-restart if in debug mode. If not, manually restart:

```bash
cd /Users/umangzala/Documents/routers/camera-stream/ocr-portal
source /Users/umangzala/Documents/routers/ocr_env/bin/activate
python app.py
```

## What to Expect

- Images saved as `router_000.png`, `router_001.png`, etc.
- Crystal clear text in captured images
- Significantly better OCR extraction results
- Larger file sizes (acceptable for quality)

