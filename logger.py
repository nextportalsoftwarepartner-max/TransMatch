# flake8: noqa: E501

import logging
import os
import sys
from datetime import datetime

# Detect PyInstaller bundle or dev mode
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# Always put logs into "log" subfolder
log_dir = os.path.join(base_dir, "log")
os.makedirs(log_dir, exist_ok=True)   # Create if not exists

log_filename = f"TransMatch_log_{datetime.now().strftime('%Y%m%d')}.txt"
log_filepath = os.path.join(log_dir, log_filename)

# Create logger instance
logger = logging.getLogger("TransMatchLogger")
logger.setLevel(logging.DEBUG)

# File Handler
file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
formatter = logging.Formatter(
    '%(asctime)s - [%(name)s][%(levelname)s] : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)

# Avoid duplicate handlers when file re-imported
if not logger.hasHandlers():
    logger.addHandler(file_handler)
