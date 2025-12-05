import logging
import sys

def setup_logger(name="MusicBridge"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Check if handlers already exist to avoid duplicates
    if not logger.handlers:
        # File Handler
        file_handler = logging.FileHandler("app.log", encoding='utf-8')
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console Handler
        # Force UTF-8 for console to handle emojis on Windows
        if sys.platform == "win32":
            sys.stdout.reconfigure(encoding='utf-8')
            
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter('%(message)s') # Keep console clean
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
    return logger
