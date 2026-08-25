# HoopSync Agent Configuration

This file contains project-specific information for the HoopSync pipeline that agents should know when working on this codebase.

## Project Overview

HoopSync is a computer vision pipeline that captures NBA 2K gameplay from Xbox, processes it frame-by-frame, extracts statistics using OCR, and stores/display/syncs the data.

## Key Commands

### Running the Pipeline
```bash
# Test video capture devices
python -m hoopsync.main --test-capture

# Run with simulator (no hardware needed)
python -m hoopsync.main --simulator --gamertag "TestPlayer"

# Run with real hardware
python -m hoopsync.main --gamertag "YourGamertag"

# Run dashboard only
python -m hoopsync.main --dashboard-only
```

### Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Test individual components
python -c "from data_acquisition import FrameCapture; FrameCapture.list_devices()"
```

### Database Operations
The database is SQLite located at `data/hoopsync.db`. You can inspect it using:
```bash
sqlite3 data/hoopsync.db
```

## Architecture Flow

1. **Frame Capture** (`data_acquisition/frame_capture.py`)
   - Captures video from Elgato HD60 X via USB
   - Provides frame generator interface
   - Includes simulator for testing without hardware

2. **Frame Detector** (`processing_engine/frame_detector.py`)
   - Classifies NBA 2K screens (scoreboard, box score, etc.)
   - Uses template matching and feature-based detection
   - Supports deep learning models

3. **ROI Extractor** (`processing_engine/roi_extractor.py`)
   - Crops regions of interest based on screen type
   - Configurable ROI definitions in config.yaml
   - Auto-detection capabilities

4. **OCR Parser** (`processing_engine/ocr_parser.py`)
   - Extracts text/numbers using Tesseract
   - Parses basketball statistics
   - Validates and cleans OCR output

5. **Database** (`local_storage_display/database.py`)
   - SQLAlchemy-based SQLite database
   - Built-in deduplication logic
   - Session and event management

6. **Dashboard** (`local_storage_display/dashboard.py`)
   - Flask-based web interface
   - Real-time statistics display
   - Leaderboards and session management

7. **Cloud Sync** (`cloud_services/cloud_sync.py`)
   - REST API client for cloud backend
   - Batch synchronization
   - Retry logic and error handling

## Configuration

Main configuration is in `config/config.yaml`:
- Video capture settings
- Detection thresholds
- ROI definitions per screen type
- OCR parameters
- Database settings
- Dashboard configuration
- Cloud sync settings

## Important Design Decisions

1. **Separation of Concerns**: Each pipeline stage is independent and can be replaced
2. **Deduplication**: Built-in at database level to prevent duplicate events from consecutive frames
3. **Modular CV**: Computer vision components can be swapped (template matching → deep learning)
4. **Database First**: Dashboard consumes database, not directly coupled to CV pipeline
5. **Async Processing**: Frame capture runs in separate thread for real-time performance

## Common Issues

### Tesseract Path Issues
- On Windows, Tesseract may not be in PATH
- Solution: Add Tesseract to system PATH or specify path in code

### Device Index Changes
- USB device index can change between reboots
- Solution: Use `--test-capture` to find current index, update config

### ROI Calibration
- ROIs are calibrated for specific NBA 2K versions/resolutions
- Solution: Use `roi_extractor.visualize_rois()` to debug and adjust

### Database Locking
- SQLite can lock with concurrent access
- Solution: Database uses connection pooling, but avoid multiple dashboard instances

## File Structure Notes

- **Models**: All data models in `processing_engine/models.py`
- **Configuration**: `config/config_loader.py` handles YAML loading with defaults
- **Logging**: Configured in `main.py`, logs to `logs/hoopsync.log`
- **Templates**: Dashboard templates generated dynamically in `dashboard.py`

## Development Workflow

1. Make changes to individual components
2. Test with simulator: `python -m hoopsync.main --simulator`
3. Test with real hardware if available
4. Check dashboard at http://localhost:8080
5. Review logs for errors

## Performance Considerations

- Frame processing is CPU-intensive
- ROI extraction reduces OCR workload
- Deduplication prevents database bloat
- Cloud sync is batched to reduce API calls
- Dashboard uses client-side polling for simplicity

## Future Enhancements

- GPU acceleration for frame processing
- Real-time deep learning screen detection
- Mobile app for remote dashboard
- WebSocket-based dashboard updates
- Advanced game analysis (shot charts, etc.)
