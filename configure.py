#!/usr/bin/env python3
"""
Configuratore interattivo per il sistema NVR
Permette di configurare telecamere, storage e Telegram in modo guidato
"""

import os
import sys
import configparser
import getpass
import ipaddress
from security_manager import SecurityManager

class NVRConfigurator:
    def __init__(self):
        self.config = configparser.RawConfigParser()
        self.config_file = "config.ini"
        self.security_manager = None
        
    def print_header(self, title):
        print("\n" + "="*60)
        print(f"🔧 {title}")
        print("="*60)
    
    def print_success(self, message):
        print(f"✅ {message}")
    
    def print_warning(self, message):
        print(f"⚠️  {message}")
    
    def print_error(self, message):
        print(f"❌ {message}")
    
    def validate_ip(self, ip):
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def validate_port(self, port):
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except ValueError:
            return False
    
    def get_input(self, prompt, default=None, required=True, validator=None):
        while True:
            if default:
                value = input(f"{prompt} [{default}]: ").strip()
                if not value:
                    value = default
            else:
                value = input(f"{prompt}: ").strip()
            
            if not value and required:
                self.print_error("Questo campo è obbligatorio!")
                continue
            
            if validator and value and not validator(value):
                self.print_error("Valore non valido!")
                continue
            
            return value
    
    def get_password(self, prompt):
        while True:
            password = getpass.getpass(f"{prompt}: ")
            if password:
                return password
            self.print_error("La password è obbligatoria!")
    
    def configure_logging(self):
        self.print_header("CONFIGURAZIONE LOGGING")
        
        log_dir = self.get_input("Directory per i log", "logs", required=False)
        
        if not self.config.has_section('Logging'):
            self.config.add_section('Logging')
        
        self.config.set('Logging', 'log_dir', log_dir)
        self.print_success("Logging configurato")
    
    def configure_storage(self):
        self.print_header("CONFIGURAZIONE STORAGE")
        
        print("Opzioni di storage:")
        print("1. Disco esterno (richiede mount point e device)")
        print("2. Cartella locale (nella directory del NVR)")
        print("3. Percorso personalizzato")
        
        choice = self.get_input("Scelta (1-3)", "2", validator=lambda x: x in ['1', '2', '3'])
        
        if not self.config.has_section('STORAGE'):
            self.config.add_section('STORAGE')
        
        # Configurazioni comuni
        rec_folder = self.get_input("Nome cartella registrazioni", "registrazioni", required=False)
        storage_size = self.get_input("Dimensione storage in GB", "450", required=False)
        storage_max_use = self.get_input("Uso massimo storage (0.0-1.0)", "0.945", required=False)
        
        self.config.set('STORAGE', 'rec_folder_name', rec_folder)
        self.config.set('STORAGE', 'storage_size', storage_size)
        self.config.set('STORAGE', 'storage_max_use', storage_max_use)
        
        if choice == '1':
            # Disco esterno
            external_device = self.get_input("Device del disco esterno (es: /dev/sdb1)")
            mount_point = self.get_input("Mount point (es: /media/TOSHIBA)")
            
            self.config.set('STORAGE', 'use_external_drive', 'true')
            self.config.set('STORAGE', 'external_device', external_device)
            self.config.set('STORAGE', 'external_mount_point', mount_point)
            
        elif choice == '3':
            # Percorso personalizzato
            custom_path = self.get_input("Percorso completo per le registrazioni")
            
            self.config.set('STORAGE', 'use_external_drive', 'false')
            self.config.set('STORAGE', 'custom_path', custom_path)
        else:
            # Cartella locale
            self.config.set('STORAGE', 'use_external_drive', 'false')
        
        self.print_success("Storage configurato")
    
    def configure_telegram(self):
        self.print_header("CONFIGURAZIONE TELEGRAM")
        
        print("Per configurare Telegram avrai bisogno di:")
        print("1. Token del bot (ottenuto da @BotFather)")
        print("2. Chat ID (ottenuto da @userinfobot)")
        print("3. IP Tailscale (opzionale, per streaming remoto)")
        
        proceed = input("\nVuoi configurare Telegram? (y/N): ").strip().lower()
        if proceed != 'y':
            self.print_warning("Configurazione Telegram saltata")
            return
        
        bot_token = self.get_input("Token del bot Telegram")
        chat_id = self.get_input("Chat ID", validator=lambda x: x.isdigit())
        tailscale_ip = self.get_input("IP Tailscale (opzionale)", required=False)
        
        if not self.config.has_section('TELEGRAM'):
            self.config.add_section('TELEGRAM')
        
        self.config.set('TELEGRAM', 'bot_token', bot_token)
        self.config.set('TELEGRAM', 'chat_id', chat_id)
        self.config.set('TELEGRAM', 'ip', tailscale_ip or '')
        
        self.print_success("Telegram configurato")
    
    def configure_cameras(self):
        self.print_header("CONFIGURAZIONE TELECAMERE")
        
        # Rimuovi telecamere esistenti se richiesto
        existing_cameras = [s for s in self.config.sections() 
                          if s.lower() not in ['logging', 'telegram', 'storage']]
        
        if existing_cameras:
            print(f"Telecamere esistenti: {', '.join(existing_cameras)}")
            remove = input("Vuoi rimuovere le telecamere esistenti? (y/N): ").strip().lower()
            if remove == 'y':
                for camera in existing_cameras:
                    self.config.remove_section(camera)
                self.print_success("Telecamere esistenti rimosse")
        
        camera_count = 0
        while True:
            camera_count += 1
            print(f"\n📹 Configurazione telecamera {camera_count}")
            
            camera_name = self.get_input("Nome telecamera (es: CameraSalotto)", required=False)
            if not camera_name:
                break
            
            # Verifica che il nome non esista già
            if self.config.has_section(camera_name):
                self.print_error(f"Telecamera {camera_name} già esistente!")
                continue
            
            camera_ip = self.get_input("Indirizzo IP", validator=self.validate_ip)
            camera_port = self.get_input("Porta", "554", validator=self.validate_port)
            camera_path = self.get_input("Percorso stream principale (es: stream1)")
            camera_path2 = self.get_input("Percorso stream secondario (es: stream2)", required=False)
            camera_username = self.get_input("Username")
            camera_password = self.get_password("Password")
            
            # Aggiungi sezione telecamera
            self.config.add_section(camera_name)
            self.config.set(camera_name, 'ip', camera_ip)
            self.config.set(camera_name, 'port', camera_port)
            self.config.set(camera_name, 'path', camera_path)
            self.config.set(camera_name, 'path2', camera_path2 or '')
            self.config.set(camera_name, 'username', camera_username)
            self.config.set(camera_name, 'password', camera_password)
            
            self.print_success(f"Telecamera {camera_name} configurata")
            
            another = input("Aggiungere un'altra telecamera? (y/N): ").strip().lower()
            if another != 'y':
                break
        
        if camera_count == 1:
            self.print_warning("Nessuna telecamera configurata")
        else:
            self.print_success(f"{camera_count-1} telecamere configurate")
    
    def save_config(self):
        self.print_header("SALVATAGGIO CONFIGURAZIONE")
        
        # Backup se esiste
        if os.path.exists(self.config_file):
            backup_file = f"{self.config_file}.backup.{int(time.time())}"
            import shutil
            shutil.copy2(self.config_file, backup_file)
            self.print_success(f"Backup creato: {backup_file}")
        
        # Salva configurazione
        with open(self.config_file, 'w') as f:
            self.config.write(f)
        
        self.print_success("Configurazione salvata")
        
        # Cifra le credenziali
        print("\n🔐 Cifratura credenziali...")
        try:
            if not self.security_manager:
                self.security_manager = SecurityManager(self.config_file)
            
            # Usa la funzione integrata in security_manager
            from security_manager import migrate_config_to_encrypted
            migrate_config_to_encrypted(self.config_file)
            self.print_success("Credenziali cifrate con successo")
        
        except Exception as e:
            self.print_error(f"Errore nella cifratura: {e}")
    
    def load_existing_config(self):
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file)
                self.print_success("Configurazione esistente caricata")
                return True
            except Exception as e:
                self.print_error(f"Errore nel caricamento: {e}")
        return False
    
    def show_menu(self):
        while True:
            self.print_header("CONFIGURATORE NVR")
            print("1. Configura logging")
            print("2. Configura storage")
            print("3. Configura Telegram")
            print("4. Configura telecamere")
            print("5. Salva configurazione")
            print("6. Mostra configurazione attuale")
            print("7. Esci")
            
            choice = input("\nScelta (1-7): ").strip()
            
            if choice == '1':
                self.configure_logging()
            elif choice == '2':
                self.configure_storage()
            elif choice == '3':
                self.configure_telegram()
            elif choice == '4':
                self.configure_cameras()
            elif choice == '5':
                self.save_config()
            elif choice == '6':
                self.show_current_config()
            elif choice == '7':
                print("👋 Arrivederci!")
                break
            else:
                self.print_error("Scelta non valida!")
    
    def show_current_config(self):
        self.print_header("CONFIGURAZIONE ATTUALE")
        
        if not self.config.sections():
            self.print_warning("Nessuna configurazione presente")
            return
        
        for section in self.config.sections():
            print(f"\n[{section}]")
            for key, value in self.config.items(section):
                # Nasconde password cifrate
                if key.lower() == 'password' and value.startswith('ENC:'):
                    print(f"  {key} = [CIFRATA]")
                elif key.lower() == 'bot_token' and value.startswith('ENC:'):
                    print(f"  {key} = [CIFRATO]")
                else:
                    print(f"  {key} = {value}")
    
    def run(self):
        print("🔧 Configuratore NVR - Sistema di configurazione interattivo")
        print("="*60)
        
        # Carica configurazione esistente
        self.load_existing_config()
        
        # Chiedi se configurazione guidata o menu
        if not self.config.sections():
            print("Nessuna configurazione trovata.")
            guided = input("Vuoi utilizzare la configurazione guidata? (Y/n): ").strip().lower()
            if guided != 'n':
                self.configure_logging()
                self.configure_storage()
                self.configure_telegram()
                self.configure_cameras()
                self.save_config()
                return
        
        # Mostra menu
        self.show_menu()

if __name__ == "__main__":
    import time
    
    # Verifica ambiente virtuale
    if not os.path.exists('venv'):
        print("❌ Ambiente virtuale non trovato!")
        print("🔧 Esegui prima: ./install.sh")
        sys.exit(1)
    
    configurator = NVRConfigurator()
    configurator.run()
