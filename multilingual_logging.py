"""
Modulo per la gestione dei log multilingua.
"""

import logging
import os
from language_manager import init_language, get_translation

class MultilingualLogFilter(logging.Filter):
    """
    Filtro di logging che traduce i messaggi in base alla lingua configurata.
    
    Questo filtro intercetta i messaggi di log e verifica se è necessario tradurli.
    I messaggi di log devono usare una speciale sintassi per essere tradotti:
    log:section.key o log:section.key:param1:param2...
    
    Esempio:
    logging.info("log:logs.disk_check")  # Messaggio semplice
    logging.error("log:logs.disk_error:%s", disk_path)  # Con parametri
    logging.warning(f"log:logs.temperature_high:{temp}")  # Con f-string
    """
    
    def __init__(self):
        """Inizializza il filtro."""
        super().__init__()
        self._load_language()
    
    def _load_language(self):
        """Carica la lingua configurata."""
        try:
            from language_manager import get_language_from_config, init_language
            language = get_language_from_config()
            init_language(language)
        except Exception:
            # Fallback all'inglese se c'è un errore
            from language_manager import init_language
            init_language('en')
    
    def filter(self, record):
        """
        Filtra e traduce il record di log se necessario.
        
        Args:
            record: Il record di log da processare
        
        Returns:
            bool: True per permettere al record di passare
        """
        # Controlla se il messaggio richiede traduzione
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # Verifica se il messaggio inizia con 'log:'
            if record.msg.startswith('log:'):
                try:
                    # Rimuovi il prefisso 'log:'
                    translation_key = record.msg[4:]
                    
                    # Dividi in sezione.chiave e parametri
                    parts = translation_key.split(':')
                    section_key = parts[0]
                    params = parts[1:] if len(parts) > 1 else []
                    
                    # Dividi sezione e chiave
                    if '.' in section_key:
                        section, key = section_key.split('.', 1)
                        
                        # Ottieni la traduzione
                        translation = get_translation(section, key, *params)
                        
                        # Sostituisci il messaggio originale con la traduzione
                        record.msg = translation
                        record.args = ()  # Resetta gli argomenti poiché li abbiamo già applicati
                    else:
                        # Se non c'è il punto, usa il messaggio originale senza prefisso
                        record.msg = record.msg[4:]
                        
                except Exception as e:
                    # In caso di errore, usa il messaggio originale senza il prefisso 'log:'
                    record.msg = record.msg[4:]
                    print(f"Errore nella traduzione del log: {e}")
        
        return True  # Permette sempre al record di passare

def setup_multilingual_logging():
    """
    Configura il logging multilingua per l'applicazione.
    Aggiunge un filtro di traduzione a tutti gli handler esistenti.
    """
    root_logger = logging.getLogger()
    
    # Crea il filtro multilingua
    multilingual_filter = MultilingualLogFilter()
    
    # Aggiunge il filtro a tutti gli handler esistenti
    for handler in root_logger.handlers:
        handler.addFilter(multilingual_filter)
    
    # Se non ci sono handler, crea un handler di base
    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        console_handler.addFilter(multilingual_filter)
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.INFO)


# Funzione di utilità per i messaggi di log tradotti
def log_translated(logger, level, section, key, *args):
    """
    Funzione di utilità per loggare messaggi già tradotti.
    
    Args:
        logger: Logger da utilizzare
        level: Livello di log (es. logging.INFO)
        section: Sezione della traduzione
        key: Chiave della traduzione
        *args: Parametri per la stringa
    """
    try:
        from language_manager import get_translation
        message = get_translation(section, key, *args)
        logger.log(level, message)
    except Exception:
        # Fallback al messaggio con chiave se la traduzione fallisce
        logger.log(level, f"{section}.{key}")
