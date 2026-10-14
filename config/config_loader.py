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
            },
            'player_attributes': {
                'player_name': [100, 180, 400, 50],
                'three_pt_shot': [100, 280, 300, 60],
                'driving_dunk': [500, 280, 300, 60],
                'mid_range': [100, 350, 300, 60],
                'standing_dunk': [500, 350, 300, 60],
                'free_throw': [100, 420, 300, 60],
                'post_control': [500, 420, 300, 60],
                'pass_accuracy': [100, 490, 300, 60],
                'ball_handle': [500, 490, 300, 60],
                'speed': [100, 560, 300, 60],
                'acceleration': [500, 560, 300, 60]
            },
            'matchup_screen': {
                'left_player_name': [100, 200, 300, 50],
                'left_ovr': [100, 260, 80, 40],
                'left_position': [200, 260, 100, 40],
                'left_height': [320, 260, 100, 40],
                'left_weight': [440, 260, 100, 40],
                'left_stat_1': [100, 320, 250, 40],
                'left_stat_2': [100, 380, 250, 40],
                'left_stat_3': [100, 440, 250, 40],
                'left_stat_4': [100, 500, 250, 40],
                'left_stat_5': [100, 560, 250, 40],
                'left_stat_6': [100, 620, 250, 40],
                'left_ppg': [100, 700, 100, 40],
                'left_rpg': [220, 700, 100, 40],
                'left_apg': [340, 700, 100, 40],
                'left_fg_pct': [460, 700, 100, 40],
                'left_3pt_pct': [580, 700, 100, 40],
                'right_player_name': [1000, 200, 300, 50],
                'right_ovr': [1000, 260, 80, 40],
                'right_position': [1100, 260, 100, 40],
                'right_height': [1220, 260, 100, 40],
                'right_weight': [1340, 260, 100, 40],
                'right_stat_1': [1000, 320, 250, 40],
                'right_stat_2': [1000, 380, 250, 40],
                'right_stat_3': [1000, 440, 250, 40],
                'right_stat_4': [1000, 500, 250, 40],
                'right_stat_5': [1000, 560, 250, 40],
                'right_stat_6': [1000, 620, 250, 40],
                'right_ppg': [1000, 700, 100, 40],
                'right_rpg': [1120, 700, 100, 40],
                'right_apg': [1240, 700, 100, 40],
                'right_fg_pct': [1360, 700, 100, 40],
                'right_3pt_pct': [1480, 700, 100, 40]
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
