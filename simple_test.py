#!/usr/bin/env python3
"""
Simple test script to verify HoopSync setup without heavy dependencies
"""

import sys
from pathlib import Path

def test_basic_setup():
    """Test basic setup without heavy dependencies"""
    print("🏀 HoopSync Basic Setup Test")
    print("=" * 40)
    
    # Test Python version
    print(f"Python version: {sys.version}")
    
    # Test directory structure
    required_dirs = ['data_acquisition', 'processing_engine', 'local_storage_display', 
                     'cloud_services', 'config', 'data', 'logs', 'models/templates']
    
    print("\nChecking directory structure:")
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✓ {dir_path}")
        else:
            print(f"✗ {dir_path} (missing)")
    
    # Test key files
    required_files = ['main.py', 'config/config.yaml', 'requirements.txt', 'README.md']
    
    print("\nChecking key files:")
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} (missing)")
    
    # Test basic imports (without heavy dependencies)
    print("\nTesting basic imports:")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import config.config_loader
        print("✓ Config loader")
    except ImportError as e:
        print(f"✗ Config loader: {e}")
    
    try:
        from processing_engine.models import ScreenType
        print("✓ Data models")
    except ImportError as e:
        print(f"✗ Data models: {e}")
    
    print("\n" + "=" * 40)
    print("Basic setup test complete!")
    print("\nTo install full dependencies:")
    print("  pip install -r requirements.txt")
    print("\nTo run HoopSync:")
    print("  python3 main.py --help")
    print("  ./hoopsync --help")

if __name__ == "__main__":
    test_basic_setup()
