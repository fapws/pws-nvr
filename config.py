import os
import configparser
import logging
import sys
import subprocess
from security_manager import SecurityManager
from secure_executor import SecureCommandExecutor

# Usa la directory corrente come OUTPUT_DIR
OUTPUT_DIR = os.getcwd()
CONFIG_FILE = os.path.join(OUTPUT_DIR, "config.ini")

# Percorso assoluto del file config.ini basato sulla posizione dello script
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

# Percorso della cartella dove si trova il file main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inizializza configparser
config = configparser.RawConfigParser()
security_manager = None
secure_executor = SecureCommandExecutor()

# 🔹 Forza la lettura di config.ini prima di assegnare i valori
if os.path.exists(CONFIG_PATH):  # Verifica che il file esista prima di leggerlo
    config.read(CONFIG_PATH)
    # Inizializza il security manager
    security_manager = SecurityManager(CONFIG_PATH)
else:
    print(f"⚠️ ATTENZIONE: File di configurazione {CONFIG_PATH} non trovato!")

# Legge la configurazione dello storage da config.ini
USE_EXTERNAL_DRIVE = config.getboolean("STORAGE", "USE_EXTERNAL_DRIVE", fallback=False)
EXTERNAL_MOUNT_POINT = config.get("STORAGE", "EXTERNAL_MOUNT_POINT", fallback="/media/TOSHIBA")
EXTERNAL_DEVICE = config.get("STORAGE", "EXTERNAL_DEVICE", fallback="/dev/sdb1")
REC_FOLDER_NAME = config.get("STORAGE", "REC_FOLDER_NAME", fallback="registrazioni")
CUSTOM_PATH = config.get("STORAGE", "CUSTOM_PATH", fallback="")
STORAGE_SIZE = config.getint("STORAGE", "STORAGE_SIZE", fallback=450)
STORAGE_MAX_USE = config.getfloat("STORAGE", "STORAGE_MAX_USE", fallback=0.95)

def mount_hard_drive():
    """ Monta l'hard disk esterno se necessario """
    if USE_EXTERNAL_DRIVE:
        if not os.path.ismount(EXTERNAL_MOUNT_POINT):
            logging.info(f"Il disco esterno non è montato. Tentativo di montare {EXTERNAL_DEVICE} su {EXTERNAL_MOUNT_POINT}.")
            try:
                os.makedirs(EXTERNAL_MOUNT_POINT, exist_ok=True)
                success, msg = secure_executor.mount_disk(EXTERNAL_DEVICE, EXTERNAL_MOUNT_POINT)
                if not success:
                    raise Exception(f"Montaggio fallito: {msg}")
                logging.info("✅ Disco esterno montato con successo.")
            except Exception as e:
                logging.critical(f"❌ Errore durante il montaggio del disco esterno: {e}")
                sys.exit(1)
        else:
            logging.info(f"✅ Il disco esterno è già montato su {EXTERNAL_MOUNT_POINT}.")

# 🔹 **Prima di creare `REGISTRAZIONI_DIR`, montiamo il disco esterno (se attivato)**
mount_hard_drive()

# 🔹 **Imposta il percorso della cartella delle registrazioni in base al tipo di storage**
if CUSTOM_PATH:
    # Percorso personalizzato
    REGISTRAZIONI_DIR = CUSTOM_PATH
    os.makedirs(REGISTRAZIONI_DIR, exist_ok=True)
elif USE_EXTERNAL_DRIVE:
    # Disco esterno
    REGISTRAZIONI_DIR = os.path.join(EXTERNAL_MOUNT_POINT, REC_FOLDER_NAME)
else:
    # Cartella locale
    REGISTRAZIONI_DIR = os.path.join(BASE_DIR, REC_FOLDER_NAME)

# 🔹 **Ora che il disco è montato, possiamo creare la cartella senza errori**
os.makedirs(REGISTRAZIONI_DIR, exist_ok=True)

# 🔹 **Log del percorso della cartella di registrazione**
logging.info(f"📂 Cartella registrazioni impostata su: {REGISTRAZIONI_DIR}")

# Recupera le credenziali di Telegram (con decifratura)
def get_telegram_credentials():
    """Recupera le credenziali Telegram cifrate"""
    if not security_manager:
        return None, 0
    
    token = config.get("TELEGRAM", "BOT_TOKEN", fallback=None)
    if token and token.startswith('ENC:'):
        token = security_manager.decrypt_password(token[4:])
    
    chat_id = config.get("TELEGRAM", "CHAT_ID", fallback="0")
    try:
        chat_id = int(chat_id)
    except ValueError:
        chat_id = 0
    
    return token, chat_id

TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID = get_telegram_credentials()

def unmount_hard_drive():
    """ Smonta l'hard disk esterno prima dello spegnimento o del riavvio """
    if USE_EXTERNAL_DRIVE and os.path.ismount(EXTERNAL_MOUNT_POINT):
        logging.info("💾 Smontaggio del disco esterno in corso...")
        try:
            success, msg = secure_executor.umount_disk(EXTERNAL_MOUNT_POINT)
            if success:
                logging.info("✅ Disco esterno smontato correttamente.")
                return True
            else:
                logging.error(f"⚠️ Errore nello smontaggio del disco: {msg}")
                return False
        except Exception as e:
            logging.error(f"⚠️ Errore nello smontaggio del disco: {e}")
            return False
    else:
        logging.info("ℹ️ Il disco esterno era già smontato.")
        return True

def load_camera_config(config_path):
    global security_manager
    config = configparser.RawConfigParser()
    if not os.path.isfile(config_path):
        logging.error(f"File di configurazione non trovato: {config_path}")
        sys.exit(1)
    config.read(config_path)
    
    # Inizializza security manager se non già fatto
    if not security_manager:
        security_manager = SecurityManager(config_path)
    
    # Crea la cartella 'registrazioni' se non esiste
    os.makedirs(REGISTRAZIONI_DIR, exist_ok=True)
    
    cameras = []
    for section in config.sections():
        if section.lower() in ["logging", "telegram", "storage", "language"]:
            continue  # Salta le sezioni di sistema
        
        camera_name = section
        camera_ip = config.get(section, "ip")
        camera_port = config.get(section, "port")
        camera_path = config.get(section, "path")
        camera_username = config.get(section, "username")
        camera_password = config.get(section, "password")
        
        # Validazione input
        if not security_manager.validate_camera_name(camera_name):
            logging.error(f"Nome telecamera non valido: {camera_name}")
            continue
        
        if not security_manager.validate_ip_address(camera_ip):
            logging.error(f"IP non valido per {camera_name}: {camera_ip}")
            continue
        
        if not security_manager.validate_port(camera_port):
            logging.error(f"Porta non valida per {camera_name}: {camera_port}")
            continue
        
        if not security_manager.validate_path(camera_path):
            logging.error(f"Percorso non valido per {camera_name}: {camera_path}")
            continue
        
        # Decifra la password se è cifrata
        if camera_password.startswith('ENC:'):
            camera_password = security_manager.decrypt_password(camera_password[4:])
            if not camera_password:
                logging.error(f"Impossibile decifrare la password per {camera_name}")
                continue
        
        # Imposta il percorso di output per i file video nella cartella 'registrazioni'
        output_path = os.path.join(REGISTRAZIONI_DIR, f"{camera_name}_%Y%m%dT%H%M%S.mkv")
        
        # Costruisci l'URL RTSP per il flusso principale
        rtsp_url = f"rtsp://{camera_username}:{camera_password}@{camera_ip}:{camera_port}/{camera_path}"
        
        camera = {
            "name": camera_name,
            "ip": camera_ip,
            "port": camera_port,
            "path": camera_path,
            "username": camera_username,
            "password": camera_password,
            "url": rtsp_url,
            "output": output_path
        }
        cameras.append(camera)
    return cameras

def load_logging_config(config_path):
    config = configparser.RawConfigParser()
    config.read(config_path)
    if config.has_section('Logging'):
        log_dir = config.get('Logging', 'log_dir', fallback=OUTPUT_DIR)
    else:
        log_dir = OUTPUT_DIR
    return log_dir

