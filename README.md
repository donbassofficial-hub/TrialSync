# 🏀 HoopSync: NBA 2K Statistics Pipeline

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

HoopSync captures NBA 2K gameplay from Xbox, processes video frame-by-frame using computer vision and OCR, stores game events locally, displays statistics on a live dashboard, and syncs data to a cloud database for shared leaderboards.

## 🌟 Features

- **Real-time Processing**: Frame-by-frame analysis of NBA 2K gameplay
- **Screen Detection**: Automatic identification of different game screens (scoreboard, box score, player stats, etc.)
- **OCR Extraction**: Accurate text and number extraction from game UI
- **Deduplication**: Smart event deduplication to prevent duplicate records
- **Live Dashboard**: Web-based dashboard for real-time statistics
- **Cloud Sync**: Optional synchronization to cloud backend
- **Advanced Metrics**: Calculates FG%, 3PT%, eFG%, TS% and more
- **Player Tracking**: Tracks teammates and opponents separately

## 🏗️ Architecture

```
Xbox → Elgato HD60 X → Local PC → HoopSync Client → Local DB → Dashboard → Cloud API → Central DB → Leaderboards
```

## 🚀 Quick Start

### Prerequisites

- Xbox with NBA 2K
- Elgato HD60 X capture card (or similar USB capture device)
- Python 3.8+
- Tesseract OCR

### Installation

```bash
# Clone the repository
git clone https://github.com/donbassofficial-hub/TrialSync.git
cd TrialSync

# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR
# macOS: brew install tesseract
# Ubuntu: sudo apt-get install tesseract-ocr
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### Run HoopSync

```bash
# Using the standalone executable (auto-checks dependencies)
./hoopsync --help

# Or with Python directly
python3 main.py --help

# Test video capture devices
python3 main.py --test-capture

# Run with simulator (no capture card needed)
python3 main.py --simulator --gamertag "TestPlayer"

# Run with real hardware
python3 main.py --gamertag "YourGamertag"

# Run dashboard only
python3 main.py --dashboard-only
```

### Access Dashboard

After starting the pipeline, access the dashboard at:
```
http://localhost:8080
```

## 📁 Project Structure

```
hoopsync/
├── data_acquisition/       # Elgato video capture
├── processing_engine/      # CV/OCR pipeline
├── local_storage_display/  # Database and dashboard
├── cloud_services/         # Cloud API sync
├── config/                 # Configuration files
├── main.py                # Pipeline orchestrator
├── hoopsync               # Standalone executable
├── run_hoopsync          # Quick run script
├── install.sh/.bat       # Installation scripts
└── deploy_to_trialsync.sh # Deployment script
```

## 📊 Pipeline Stages

1. **Data Acquisition**: Xbox → Elgato HD60 X via HDMI/USB
2. **Processing Engine**: Frame Capture → Frame Detector → ROI Extractor → OCR Parser
3. **Local Storage**: Event Database with deduplication
4. **Display**: Live User Dashboard
5. **Cloud**: Structured data sync to central database

## ⚙️ Configuration

Edit `config/config.yaml` to customize settings:

```yaml
video_capture:
  device_index: 0  # May need adjustment based on your system
  width: 1920
  height: 1080
  fps: 30

cloud:
  enabled: false  # Set to true and add API key for cloud sync
  api_key: "your-api-key"
```

## 📈 Data Models

### GameEvent
- Player statistics (PTS, REB, AST, etc.)
- Player attributes (build ratings)
- Detection confidence and OCR confidence
- Timestamp and session info

### PlayerStats
- Basic: Points, rebounds, assists, steals, blocks, turnovers
- Shooting: FG%, 3PT%, FT%
- Advanced: eFG%, TS%

## 🔧 Troubleshooting

### Capture Card Not Detected
- Check USB connection (use USB 3.0+)
- Run `--test-capture` to find correct device index
- Verify Elgato software works

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### Tesseract Not Found
- macOS: `brew install tesseract`
- Ubuntu: `sudo apt-get install tesseract-ocr`
- Windows: Download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

## 📚 Documentation

- **QUICKSTART.md**: Quick start guide
- **INSTALLATION.md**: Detailed installation instructions
- **AGENTS.md**: Development guidelines for agents

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [OpenCV](https://opencv.org/)
- OCR powered by [Tesseract](https://github.com/tesseract-ocr/tesseract)
- Web dashboard with [Flask](https://flask.palletsprojects.com/)

---

**Made with ❤️ for NBA 2K players and statisticians**
