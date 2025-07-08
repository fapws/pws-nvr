import requests
import configparser
import os
from security_manager import SecurityManager

# Carica il supporto multilingua se disponibile
try:
    from language_manager import init_language, get_translation
    # Inizializza il gestore lingue (legge automaticamente da config.ini)
    init_language()
    multilang_support = True
except Exception as e:
    print(f"Errore caricamento lingua: {e}")
    multilang_support = False
except ImportError:
    multilang_support = False

# Percorso assoluto del file di configurazione Telegram
TELEGRAM_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

# Legge il file di configurazione Telegram
config = configparser.RawConfigParser()
config.read(TELEGRAM_CONFIG_PATH)

# Inizializza security manager per decifrare le credenziali
try:
    security_manager = SecurityManager(TELEGRAM_CONFIG_PATH)
except Exception as e:
    print(f"⚠️ Errore nell'inizializzazione del security manager: {e}")
    security_manager = None

def get_telegram_credentials():
    """Recupera le credenziali Telegram cifrate"""
    if not security_manager:
        return None, None
    
    # Recupera token
    token = config.get("TELEGRAM", "BOT_TOKEN", fallback=None)
    if token and token.startswith('ENC:'):
        token = security_manager.decrypt_password(token[4:])
    
    # Recupera chat ID
    chat_id = config.get("TELEGRAM", "CHAT_ID", fallback=None)
    
    return token, chat_id

# Recupera le credenziali
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID = get_telegram_credentials()

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Errore: Credenziali Telegram mancanti in telegram_config.ini")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Errore nell'invio della notifica Telegram: {e}")
        return None
