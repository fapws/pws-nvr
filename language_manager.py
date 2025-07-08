"""
Modulo per il supporto multilingua del sistema NVR.
"""

import os
import json
import logging
import configparser

class LanguageManager:
    """Gestore delle traduzioni per il supporto multilingua."""
    
    def __init__(self, language='en'):
        """
        Inizializza il gestore delle traduzioni.
        
        Args:
            language (str): Codice lingua da utilizzare (default: 'en')
        """
        self.language = language
        self.translations = {}
        self.available_languages = self._get_available_languages()
        self.load_language(language)
    
    def _get_available_languages(self):
        """
        Rileva le lingue disponibili nella cartella lang.
        
        Returns:
            list: Lista dei codici lingua disponibili
        """
        lang_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lang')
        available = []
        
        try:
            for file in os.listdir(lang_dir):
                if file.endswith('.json'):
                    lang_code = os.path.splitext(file)[0]
                    available.append(lang_code)
        except FileNotFoundError:
            logging.error("Directory delle traduzioni non trovata.")
            return ['en']  # Fallback alla lingua inglese
        
        return available if available else ['en']
    
    def load_language(self, language):
        """
        Carica un file di lingua.
        
        Args:
            language (str): Codice lingua da caricare
        
        Returns:
            bool: True se il caricamento è avvenuto con successo
        """
        if language not in self.available_languages:
            logging.warning(f"Lingua '{language}' non disponibile. Uso 'en' come fallback.")
            language = 'en'
        
        lang_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lang', f"{language}.json")
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.language = language
            return True
        except Exception as e:
            logging.error(f"Errore caricamento lingua '{language}': {e}")
            # Se fallisce e non è già inglese, prova a caricare l'inglese
            if language != 'en':
                return self.load_language('en')
            return False
    
    def get(self, section, key, *args):
        """
        Ottiene una traduzione con supporto per parametri.
        
        Args:
            section (str): Sezione del file di traduzione (es. 'install', 'bot')
            key (str): Chiave della traduzione
            *args: Parametri opzionali per il formato della stringa
        
        Returns:
            str: Testo tradotto o chiave se non trovata
        """
        try:
            text = self.translations.get(section, {}).get(key, f"{section}.{key}")
            if args:
                return text % args
            return text
        except Exception as e:
            logging.error(f"Errore nell'ottenere traduzione per {section}.{key}: {e}")
            return f"{section}.{key}"
    
    def get_available_languages_names(self):
        """
        Restituisce i nomi delle lingue disponibili.
        
        Returns:
            dict: Dizionario con codice lingua come chiave e nome come valore
        """
        language_names = {
            'en': 'English',
            'it': 'Italiano'
            # Aggiungere altre lingue qui quando supportate
        }
        
        # Filtra solo le lingue effettivamente disponibili
        return {code: name for code, name in language_names.items() 
                if code in self.available_languages}


# Singleton globale per accesso facile alle traduzioni
_language_manager = None

def get_language_from_config(config_file=None):
    """
    Legge la lingua configurata dal file config.ini.
    
    Args:
        config_file (str): Percorso del file di configurazione (opzionale)
    
    Returns:
        str: Codice lingua configurato o 'en' come default
    """
    if config_file is None:
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    
    try:
        config = configparser.RawConfigParser()
        config.read(config_file)
        
        # Legge la lingua dalla sezione [LANGUAGE]
        language = config.get('LANGUAGE', 'language', fallback='en')
        return language
    except Exception as e:
        logging.error(f"Errore lettura lingua da config.ini: {e}")
        return 'en'

def init_language(language=None):
    """
    Inizializza il gestore lingue globale.
    
    Args:
        language (str): Codice lingua da utilizzare (se None, legge da config.ini)
    
    Returns:
        LanguageManager: Istanza del gestore lingue
    """
    global _language_manager
    
    if language is None:
        language = get_language_from_config()
    
    _language_manager = LanguageManager(language)
    return _language_manager

def get_translation(section, key, *args):
    """
    Funzione di utilità per ottenere traduzioni.
    
    Args:
        section (str): Sezione del file di traduzione
        key (str): Chiave della traduzione
        *args: Parametri opzionali per il formato della stringa
    
    Returns:
        str: Testo tradotto
    """
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    
    return _language_manager.get(section, key, *args)

def get_language_manager():
    """
    Ottiene l'istanza del gestore lingue.
    
    Returns:
        LanguageManager: Istanza del gestore lingue
    """
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    
    return _language_manager
