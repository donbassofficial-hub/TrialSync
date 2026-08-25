"""
Processing Engine Module
Handles CV/OCR pipeline for frame detection and data extraction
"""

from .models import (
    Frame, DetectionResult, ROI, ExtractedRegion, OCRResult,
    PlayerStats, PlayerAttributes, GameEvent, GameSession, ScreenType
)
from .frame_detector import FrameDetector, ScreenClassifier
from .roi_extractor import ROIExtractor, DynamicROIExtractor
from .ocr_parser import OCRParser, StatParser

__all__ = [
    'Frame', 'DetectionResult', 'ROI', 'ExtractedRegion', 'OCRResult',
    'PlayerStats', 'PlayerAttributes', 'GameEvent', 'GameSession', 'ScreenType',
    'FrameDetector', 'ScreenClassifier', 'ROIExtractor', 'DynamicROIExtractor',
    'OCRParser', 'StatParser'
]
