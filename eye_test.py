import cv2
import argparse
import csv
import json
import os
import urllib.request
import time
from datetime import datetime
from collections import deque

# 1. Setup both models (Face and Eye)
face_xml = 'haarcascade_frontalface_default.xml'
eye_xml = 'haarcascade_eye.xml'

FOCUSED_THRESHOLD = 0.6
ALERT_AFTER_SECONDS = 2.5
MIN_TUNE_SAMPLES = 60
DEFAULT_CAMERA_INDEX = 0

DEFAULT_CONFIG = {
    "camera_index": DEFAULT_CAMERA_INDEX,
    "focused_threshold": FOCUSED_THRESHOLD,
    "alert_after_seconds": ALERT_AFTER_SECONDS,
}


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def normalize_config(config):
    """Clamp and normalize config values into safe runtime bounds."""
    return {
        "camera_index": max(0, int(config.get("camera_index", DEFAULT_CAMERA_INDEX))),
        "focused_threshold": clamp(float(config.get("focused_threshold", FOCUSED_THRESHOLD)), 0.1, 0.95),
        "alert_after_seconds": clamp(float(config.get("alert_after_seconds", ALERT_AFTER_SECONDS)), 0.5, 10.0),
    }


"""Backward-compatible wrapper for running the tracker from the old script path."""

from focussight.tracker import *  # noqa: F401,F403
from focussight.tracker import main


if __name__ == "__main__":
    main()