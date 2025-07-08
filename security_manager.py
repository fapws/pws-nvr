#!/usr/bin/env python3
"""
Security Manager per il sistema NVR
Gestisce la cifratura delle credenziali e la validazione degli input
"""

import os
import base64
import hashlib
import configparser
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import re
import ipaddress

class SecurityManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self.key_file = os.path.join(os.path.dirname(config_file), ".nvr_key")
        self.cipher_suite = None
        self._init_encryption()
    
    def _init_encryption(self):
        """Inizializza il sistema di cifratura"""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            # Genera una nuova chiave basata su password master
            password = os.getenv('NVR_MASTER_PASSWORD', 'nvr_default_key_2025').encode()
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            # Salva la chiave (solo per il primo avvio)
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)  # Solo proprietario può leggere
        
        self.cipher_suite = Fernet(key)
    
    def encrypt_password(self, password):
        """Cifra una password"""
        return self.cipher_suite.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password):
        """Decifra una password"""
        try:
            return self.cipher_suite.decrypt(encrypted_password.encode()).decode()
        except Exception as e:
            logging.error(f"Errore nella decifratura: {e}")
            return None
    
    def validate_ip_address(self, ip):
        """Valida un indirizzo IP"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def validate_port(self, port):
        """Valida una porta"""
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except ValueError:
            return False
    
    def validate_camera_name(self, name):
        """Valida il nome della telecamera (solo caratteri alfanumerici e underscore)"""
        return re.match(r'^[a-zA-Z0-9_]+$', name) is not None
    
    def validate_path(self, path):
        """Valida il percorso RTSP"""
        # Controllo base per evitare path traversal
        if '../' in path or '..' in path:
            return False
        return re.match(r'^[a-zA-Z0-9_/.-]+$', path) is not None
    
    def sanitize_ffmpeg_command(self, cmd_list):
        """Sanitizza i comandi FFmpeg per il logging"""
        sanitized = []
        for i, arg in enumerate(cmd_list):
            if i > 0 and cmd_list[i-1] == '-i':
                # Nasconde le credenziali nell'URL RTSP
                sanitized.append(self._hide_credentials_in_url(arg))
            else:
                sanitized.append(arg)
        return sanitized
    
    def _hide_credentials_in_url(self, url):
        """Nasconde le credenziali in un URL RTSP"""
        pattern = r'rtsp://([^:]+):([^@]+)@(.+)'
        match = re.match(pattern, url)
        if match:
            return f"rtsp://***:***@{match.group(3)}"
        return url
    
    def validate_telegram_token(self, token):
        """Valida il formato del token Telegram"""
        return re.match(r'^\d+:[A-Za-z0-9_-]+$', token) is not None
    
    def validate_chat_id(self, chat_id):
        """Valida il Chat ID Telegram"""
        try:
            int(chat_id)
            return True
        except ValueError:
            return False

def migrate_config_to_encrypted(config_file):
    """Migra le password in chiaro a formato cifrato - INTEGRATA"""
    security_manager = SecurityManager(config_file)
    config = configparser.RawConfigParser()
    config.read(config_file)
    
    modified = False
    
    # Cifra le password delle telecamere
    for section in config.sections():
        if section.lower() not in ['logging', 'telegram', 'storage']:
            if config.has_option(section, 'password'):
                password = config.get(section, 'password')
                if not password.startswith('ENC:'):  # Se non è già cifrata
                    encrypted_password = security_manager.encrypt_password(password)
                    config.set(section, 'password', f'ENC:{encrypted_password}')
                    modified = True
    
    # Cifra il token Telegram
    if config.has_section('TELEGRAM'):
        if config.has_option('TELEGRAM', 'bot_token'):
            token = config.get('TELEGRAM', 'bot_token')
            if not token.startswith('ENC:'):
                encrypted_token = security_manager.encrypt_password(token)
                config.set('TELEGRAM', 'bot_token', f'ENC:{encrypted_token}')
                modified = True
    
    if modified:
        # Backup del file originale
        import time
        backup_file = f"{config_file}.backup.{int(time.time())}"
        import shutil
        shutil.copy2(config_file, backup_file)
        
        # Salva la configurazione cifrata
        with open(config_file, 'w') as f:
            config.write(f)
        
        # Imposta permessi restrittivi
        import os
        os.chmod(config_file, 0o600)
        
        print(f"✅ Configurazione migrata a formato cifrato. Backup: {backup_file}")
    
    return security_manager

if __name__ == "__main__":
    import time
    # Test di migrazione
    config_file = "config.ini"
    if os.path.exists(config_file):
        migrate_config_to_encrypted(config_file)
