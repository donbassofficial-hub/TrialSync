"""
Configuration loader for HoopSync
"""

import yaml
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        logger.warning(f"Config file not found at {config_path}, using defaults")
        return get_default_config()
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Configuration loaded from {config_path}")
        return config or {}
        
    except Exception as e:
        logger.error(f"Error loading config: {e}, using defaults")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration
    
    Returns:
        Default configuration dictionary
    """
    return {
        'video_capture': {
            'device_index': 0,
            'width': 1920,
            'height': 1080,
            'fps': 30,
            'buffer_size': 10
        },
        'frame_detector': {
            'confidence_threshold': 0.75,
            'model_path': 'models/screen_detector.pth',
            'screen_types': [
                'scoreboard', 'box_score', 'player_stats', 'team_stats',
                'matchup_screen', 'player_card', 'player_attributes',
                'shot_info', 'game_summary', 'final_results'
            ]
        },
        'roi_extractor': {
            'scoreboard': {
                'player_name': [100, 200, 300, 50],
                'points': [350, 200, 100, 50],
                'rebounds': [460, 200, 100, 50],
                'assists': [570, 200, 100, 50]
            },
            'box_score': {
                'player_name': [50, 100, 200, 40],
                'fg': [260, 100, 80, 40],
                'three_pt': [350, 100, 80, 40],
                'ft': [440, 100, 80, 40],
                'pts': [530, 100, 60, 40],
                'reb': [600, 100, 60, 40],
                'ast': [670, 100, 60, 40],
                'stl': [740, 100, 60, 40],
                'blk': [810, 100, 60, 40],
                'tov': [880, 100, 60, 40]
            }
        },
        'ocr': {
            'engine': 'tesseract',
            'language': 'eng',
            'confidence_threshold': 0.7,
            'preprocessing': {
                'grayscale': True,
                'threshold': True,
                'denoise': True
            }
        },
        'database': {
            'type': 'sqlite',
            'path': 'data/hoopsync.db',
            'pool_size': 5
        },
        'deduplication': {
            'time_window_seconds': 5,
            'similarity_threshold': 0.95
        },
        'dashboard': {
            'host': '127.0.0.1',
            'port': 8080,
            'refresh_rate_ms': 1000
        },
        'cloud': {
            'enabled': False,
            'api_endpoint': 'https://api.hoopsync.com',
            'api_key': '',
            'sync_interval_seconds': 60,
            'retry_attempts': 3,
            'timeout_seconds': 30
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/hoopsync.log',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    }


def save_config(config: Dict[str, Any], config_path: str = "config/config.yaml"):
    """
    Save configuration to YAML file
    
    Args:
        config: Configuration dictionary
        config_path: Path to save configuration file
    """
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"Configuration saved to {config_path}")
        
    except Exception as e:
        logger.error(f"Error saving config: {e}")
