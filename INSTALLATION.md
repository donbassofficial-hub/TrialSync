# HoopSync Installation Guide

## Prerequisites

### Hardware Requirements
- **Xbox** (Xbox One, Xbox Series S/X) running NBA 2K
- **Elgato HD60 X** capture card (or similar USB capture device)
- **Local PC** with:
  - USB 3.0+ port for capture card
  - Minimum 8GB RAM (16GB recommended)
  - Modern CPU with multi-core support
  - Storage space for video buffer and database

### Software Requirements
- **Operating System**: Windows 10/11, macOS 10.15+, or Linux
- **Python**: 3.8 or higher
- **Tesseract OCR**: Latest version

## Installation Steps

### 1. Clone or Download the Project

```bash
cd /path/to/your/projects
git clone <repository-url> hoopsync
cd hoopsync
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Tesseract OCR

#### Windows
1. Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install Tesseract (note the installation path)
3. Add Tesseract to your system PATH
4. Verify installation: `tesseract --version`

#### macOS
```bash
brew install tesseract
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

### 4. Configure Hardware

#### Elgato HD60 X Setup
1. Connect Xbox to Elgato HD60 X via HDMI
2. Connect Elgato HD60 X to PC via USB 3.0+
3. Connect Elgato HDMI output to TV/monitor (optional)
4. Install Elgato software to verify capture card works
5. Note the device index (usually 0, but may vary)

#### Test Video Capture
```bash
python -m hoopsync.main --test-capture
```

This will list available video capture devices.

### 5. Configure HoopSync

Edit `config/config.yaml`:

```yaml
# Video Capture Settings
video_capture:
  device_index: 0  # Change if needed based on test-capture output
  width: 1920
  height: 1080
  fps: 30

# Adjust other settings as needed
```

### 6. Create Required Directories

```bash
mkdir -p data logs models/templates
```

### 7. Optional: Train Screen Detection Model

For production use, you may want to train a custom screen detection model:

1. Collect sample images of each NBA 2K screen type
2. Organize in `models/training_data/` by screen type
3. Train the model (training script to be provided)
4. Update `config.yaml` with model path

## Verification

### Test with Simulator

To test the pipeline without capture card:

```bash
python -m hoopsync.main --simulator --gamertag "TestPlayer"
```

### Test with Real Hardware

```bash
python -m hoopsync.main --gamertag "YourGamertag"
```

### Test Dashboard

```bash
python -m hoopsync.main --dashboard-only
```

Then open http://localhost:8080 in your browser.

## Troubleshooting

### Tesseract Not Found
- Ensure Tesseract is installed and in system PATH
- On Windows, you may need to specify the path in code
- On Linux, install language packs: `sudo apt-get install tesseract-ocr-eng`

### Capture Card Not Detected
- Check USB connection (use USB 3.0+ port)
- Verify Elgato software can detect the device
- Try different device_index values in config
- Check device permissions on Linux

### Poor OCR Results
- Ensure video resolution is at least 1080p
- Check ROI definitions in config match your NBA 2K version
- Improve lighting conditions
- Consider training custom OCR model

### High CPU Usage
- Reduce FPS in config
- Lower video resolution
- Close unnecessary applications
- Consider GPU acceleration for processing

## Next Steps

1. Run the simulator to test the pipeline
2. Test with real NBA 2K gameplay
3. Calibrate ROI definitions for your NBA 2K version
4. Set up cloud sync if desired
5. Customize dashboard as needed

## Support

For issues and questions:
- Check logs in `logs/hoopsync.log`
- Review configuration in `config/config.yaml`
- Test individual components using test scripts
