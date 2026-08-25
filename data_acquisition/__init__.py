"""
Data Acquisition Module
Handles video capture from Elgato HD60 X
"""

from .frame_capture import FrameCapture, FrameCaptureSimulator

__all__ = ['FrameCapture', 'FrameCaptureSimulator']
