"""
Basic test script to verify HoopSync setup
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    # First check if dependencies are available
    try:
        import yaml
        print("✓ PyYAML is available")
    except ImportError:
        print("✗ PyYAML not installed. Run: pip install pyyaml")
        return False
    
    try:
        import cv2
        print("✓ OpenCV is available")
    except ImportError:
        print("✗ OpenCV not installed. Run: pip install opencv-python")
        return False
    
    try:
        import pytesseract
        print("✓ Tesseract is available")
    except ImportError:
        print("✗ Tesseract not installed. Run: pip install pytesseract")
        return False
    
    try:
        from hoopsync.config.config_loader import load_config
        print("✓ Config loader imports successfully")
    except Exception as e:
        print(f"✗ Config loader import failed: {e}")
        return False
    
    try:
        from hoopsync.processing_engine.models import (
            Frame, DetectionResult, ROI, ExtractedRegion, OCRResult,
            PlayerStats, PlayerAttributes, GameEvent, GameSession, ScreenType
        )
        print("✓ Data models import successfully")
    except Exception as e:
        print(f"✗ Data models import failed: {e}")
        return False
    
    try:
        from hoopsync.data_acquisition import FrameCapture, FrameCaptureSimulator
        print("✓ Data acquisition imports successfully")
    except Exception as e:
        print(f"✗ Data acquisition import failed: {e}")
        return False
    
    try:
        from hoopsync.processing_engine import (
            FrameDetector, ROIExtractor, OCRParser, StatParser
        )
        print("✓ Processing engine imports successfully")
    except Exception as e:
        print(f"✗ Processing engine import failed: {e}")
        return False
    
    try:
        from hoopsync.local_storage_display import LocalEventDatabase, Dashboard
        print("✓ Local storage display imports successfully")
    except Exception as e:
        print(f"✗ Local storage display import failed: {e}")
        return False
    
    try:
        from hoopsync.cloud_services import CloudSync, CloudAPI
        print("✓ Cloud services imports successfully")
    except Exception as e:
        print(f"✗ Cloud services import failed: {e}")
        return False
    
    return True


def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from hoopsync.config.config_loader import load_config
        config = load_config()
        
        print(f"✓ Configuration loaded successfully")
        print(f"  - Video capture device: {config.get('video_capture', {}).get('device_index')}")
        print(f"  - Database path: {config.get('database', {}).get('path')}")
        print(f"  - Cloud sync enabled: {config.get('cloud', {}).get('enabled')}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_models():
    """Test data models"""
    print("\nTesting data models...")
    
    try:
        from hoopsync.processing_engine.models import (
            PlayerStats, GameEvent, ScreenType
        )
        
        # Create a PlayerStats object
        stats = PlayerStats(
            player_name="Test Player",
            points=24,
            rebounds=7,
            assists=11,
            fg_made=9,
            fg_attempted=15
        )
        
        print(f"✓ PlayerStats created: {stats.player_name}")
        print(f"  - FG%: {stats.fg_percentage:.1f}%")
        
        # Create a GameEvent
        event = GameEvent(
            game_session_id="test-session",
            event_type="box_score",
            player_name="Test Player",
            screen_source=ScreenType.BOX_SCORE,
            stats=stats
        )
        
        print(f"✓ GameEvent created: {event.event_id}")
        
        return True
    except Exception as e:
        print(f"✗ Data models test failed: {e}")
        return False


def test_directories():
    """Test that required directories exist"""
    print("\nTesting directories...")
    
    required_dirs = ['data', 'logs', 'models/templates', 'config']
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✓ {dir_path} exists")
        else:
            print(f"✗ {dir_path} missing")
            all_exist = False
    
    return all_exist


def main():
    """Run all tests"""
    print("=" * 50)
    print("HoopSync Setup Test")
    print("=" * 50)
    
    tests = [
        ("Directories", test_directories),
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Data Models", test_models)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! HoopSync is ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
