# HoopSync Quick Start Guide

## 🚀 Quick Start

### Option 1: Direct Execution (Recommended)

```bash
# Navigate to the hoopsync directory
cd hoopsync

# Install dependencies
pip install -r requirements.txt

# Run the executable
./run_hoopsync --help

# Or run directly with Python
python3 main.py --help
```

### Option 2: Using Installation Scripts

#### macOS/Linux:
```bash
cd hoopsync
./install.sh
./run_hoopsync --help
```

#### Windows:
```cmd
cd hoopsync
install.bat
run_hoopsync.bat --help
```

## 📋 Available Commands

```bash
# Test video capture devices
python3 main.py --test-capture

# Run with simulator (no hardware needed)
python3 main.py --simulator --gamertag "TestPlayer"

# Run with real hardware
python3 main.py --gamertag "YourGamertag"

# Run dashboard only
python3 main.py --dashboard-only

# Show help
python3 main.py --help
```

## 🔧 First-Time Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test Video Capture**
   ```bash
   python3 main.py --test-capture
   ```
   This will show available video devices. Note the device index for your Elgato capture card.

3. **Configure Settings**
   Edit `config/config.yaml` to set:
   - `video_capture.device_index` (from step 2)
   - Other settings as needed

4. **Test with Simulator**
   ```bash
   python3 main.py --simulator --gamertag "TestPlayer"
   ```

5. **Run with Real Hardware**
   ```bash
   python3 main.py --gamertag "YourGamertag"
   ```

## 🌐 Access Dashboard

After starting the pipeline, access the dashboard at:
```
http://localhost:8080
```

## 📦 Deploy to TrialSync Repository

To push this to your GitHub repository:

```bash
cd hoopsync
./deploy_to_trialsync.sh
```

Or manually:

```bash
git init
git add .
git commit -m "Initial HoopSync implementation"
git remote add origin https://github.com/donbassofficial-hub/TrialSync.git
git push -u origin main
```

## 🐛 Troubleshooting

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### Tesseract Not Found
- macOS: `brew install tesseract`
- Ubuntu: `sudo apt-get install tesseract-ocr`
- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki

### Camera Not Detected
- Check USB connection
- Run `python3 main.py --test-capture` to find correct device index
- Update `config/config.yaml` with correct device index

### Import Errors
Make sure you're running from the hoopsync directory:
```bash
cd hoopsync
python3 main.py --help
```

## 📚 Documentation

- **README.md**: Complete project overview
- **INSTALLATION.md**: Detailed installation instructions
- **AGENTS.md**: Development guidelines for agents
- **config/config.yaml**: Configuration reference

## 🎯 Next Steps

1. ✅ Install dependencies
2. ✅ Test video capture
3. ✅ Configure settings
4. ✅ Test with simulator
5. ✅ Run with real hardware
6. ✅ Access dashboard
7. ✅ Deploy to GitHub
