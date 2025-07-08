import os
import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logging(log_dir):
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "record_cameras.log")
    
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # <--- Imposta il livello DEBUG

    # Rimuove tutti gli handler esistenti per evitare duplicati
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Handler per la rotazione dei file di log
    rotating_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5  # Mantiene fino a 5 file di backup
    )
    rotating_handler.setLevel(logging.DEBUG)  # <--- Anche qui DEBUG
    
    # Formato dei log
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    rotating_handler.setFormatter(formatter)
    
    # Handler per lo stream (console)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)  # <--- Anche qui DEBUG
    stream_handler.setFormatter(formatter)
    
    # Aggiungi gli handler al logger
    logger.addHandler(rotating_handler)
    logger.addHandler(stream_handler)
    
    return log_file
