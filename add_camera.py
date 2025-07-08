#!/usr/bin/env python3
"""
Script per aggiungere nuove telecamere al sistema NVR
"""
import os
import sys
import configparser
import subprocess
from security_manager import SecurityManager
from language_manager import init_language, get_translation

def add_camera_interactive():
    """Aggiunge una telecamera in modo interattivo"""
    
    # Inizializza il gestore lingue
    try:
        init_language()
    except:
        init_language("en")
    
    print("=" * 50)
    print(get_translation("add_camera", "title"))
    print("=" * 50)
    
    # Verifica che il sistema sia installato
    if not os.path.exists("config.ini"):
        print(get_translation("add_camera", "system_not_found"))
        return False
    
    # Leggi configurazione esistente
    config = configparser.ConfigParser()
    config.read("config.ini")
    
    # Chiedi i dati della telecamera
    print(f"\n{get_translation('add_camera', 'enter_data')}")
    
    camera_name = input(get_translation("add_camera", "camera_name") + " ").strip()
    if not camera_name:
        print(get_translation("add_camera", "name_required"))
        return False
    
    # Verifica che il nome non esista già
    if camera_name in config.sections():
        print(get_translation("add_camera", "name_exists") % camera_name)
        return False
    
    camera_ip = input(get_translation("add_camera", "camera_ip") + " ").strip()
    if not camera_ip:
        print(get_translation("add_camera", "ip_required"))
        return False
    
    camera_port = input(get_translation("add_camera", "camera_port") + " ").strip()
    if not camera_port:
        camera_port = "554"
    
    camera_path = input(get_translation("add_camera", "primary_stream") + " ").strip()
    if not camera_path:
        camera_path = "/stream1"
    
    camera_path2 = input(get_translation("add_camera", "secondary_stream") + " ").strip()
    if not camera_path2:
        camera_path2 = "/stream2"
    
    camera_username = input(get_translation("add_camera", "username") + " ").strip()
    camera_password = input(get_translation("add_camera", "password") + " ").strip()
    
    # Test connessione
    print(f"\n{get_translation('add_camera', 'testing_connection') % (camera_ip, camera_port)}")
    if test_camera_connection(camera_ip, camera_port, camera_username, camera_password, camera_path):
        print(get_translation("add_camera", "connection_success"))
    else:
        print(get_translation("add_camera", "connection_failed"), end="")
        if input().lower() != 'y':
            print(get_translation("add_camera", "addition_cancelled"))
            return False
    
    # Cifra solo la password se presente (l'username rimane in chiaro)
    security_manager = SecurityManager("config.ini")
    
    if camera_password:
        camera_password = "ENC:" + security_manager.encrypt_password(camera_password)
    
    # Aggiungi la sezione alla configurazione
    config.add_section(camera_name)
    config.set(camera_name, "ip", camera_ip)
    config.set(camera_name, "port", camera_port)
    config.set(camera_name, "path", camera_path)
    config.set(camera_name, "path2", camera_path2)
    config.set(camera_name, "username", camera_username)
    config.set(camera_name, "password", camera_password)
    
    # Salva la configurazione
    with open("config.ini", "w") as config_file:
        config.write(config_file)
    
    print(f"\n{get_translation('add_camera', 'camera_added') % camera_name}")
    print(f"\n{get_translation('add_camera', 'apply_changes')}")
    print("   sudo systemctl restart nvr")
    print(f"\n{get_translation('add_camera', 'useful_commands')}")
    print(get_translation("add_camera", "check_status"))
    print(get_translation("add_camera", "monitor_log"))
    print(get_translation("add_camera", "camera_log") % camera_name)
    
    # Chiedi se riavviare automaticamente
    print(f"\n{get_translation('add_camera', 'restart_service')}", end="")
    if input().lower() == 'y':
        print(get_translation("add_camera", "restarting_nvr"))
        result = subprocess.run(["sudo", "systemctl", "restart", "nvr"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(get_translation("add_camera", "restart_success"))
        else:
            print(get_translation("add_camera", "restart_error") % result.stderr)
    
    return True

def test_camera_connection(ip, port, username, password, path):
    """Testa la connessione alla telecamera con diagnostica migliorata"""
    try:
        # Costruisci URL RTSP
        if username and password:
            rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}{path}"
            # Per il debug, nascondi la password
            debug_url = f"rtsp://{username}:***@{ip}:{port}{path}"
        else:
            rtsp_url = f"rtsp://{ip}:{port}{path}"
            debug_url = rtsp_url
        
        print(f"   {get_translation('add_camera', 'testing_url')}: {debug_url}")
        
        # Test con ffprobe (più permissivo)
        result = subprocess.run([
            "ffprobe", 
            "-v", "error",  # Cambiato da quiet a error per vedere più informazioni
            "-select_streams", "v:0", 
            "-show_entries", "stream=codec_name,width,height", 
            "-of", "csv=s=x:p=0",
            "-rtsp_transport", "tcp",  # Forza TCP
            "-timeout", "10000000",   # 10 secondi timeout (corretto per ffprobe)
            rtsp_url
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print(f"   Stream info: {result.stdout.strip()}")
            return True
        else:
            # Se ffprobe fallisce, prova un test più semplice
            print(f"   ffprobe error: {result.stderr.strip()}")
            print(f"   {get_translation('add_camera', 'trying_simple_test')}")
            
            # Test più semplice: verifica solo se possiamo connetterci
            simple_result = subprocess.run([
                "ffprobe", 
                "-v", "fatal",
                "-t", "5",  # Leggi solo 5 secondi
                rtsp_url
            ], capture_output=True, text=True, timeout=10)
            
            if simple_result.returncode == 0:
                print(f"   {get_translation('add_camera', 'simple_test_success')}")
                return True
            else:
                print(f"   {get_translation('add_camera', 'simple_test_failed')}: {simple_result.stderr.strip()}")
                return False
                
    except subprocess.TimeoutExpired:
        print(f"   {get_translation('add_camera', 'connection_timeout')}")
        return False
    except Exception as e:
        print(get_translation("add_camera", "connection_test_error") % str(e))
        return False

def list_cameras():
    """Mostra l'elenco delle telecamere configurate"""
    if not os.path.exists("config.ini"):
        print(get_translation("add_camera", "config_not_found"))
        return
    
    config = configparser.ConfigParser()
    config.read("config.ini")
    
    # Filtra solo le sezioni che rappresentano telecamere
    cameras = [section for section in config.sections() 
               if section not in ["Logging", "LANGUAGE", "STORAGE", "TELEGRAM"]]
    
    print("=" * 50)
    print(get_translation("add_camera", "cameras_configured"))
    print("=" * 50)
    
    if not cameras:
        print(get_translation("add_camera", "no_cameras"))
        return
    
    for camera in cameras:
        try:
            ip = config.get(camera, "ip", fallback="N/A")
            port = config.get(camera, "port", fallback="554")
            path = config.get(camera, "path", fallback="N/A")
            
            print(f"\n{get_translation('add_camera', 'camera_info') % camera}")
            print(get_translation("add_camera", "camera_ip_port") % (ip, port))
            print(get_translation("add_camera", "camera_stream") % path)
            print(get_translation("add_camera", "camera_log_path") % camera)
        except Exception as e:
            print(get_translation("add_camera", "config_read_error") % (camera, str(e)))

def main():
    """Menu principale"""
    # Inizializza il gestore lingue
    try:
        init_language()
    except:
        init_language("en")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_cameras()
            return
        elif sys.argv[1] == "add":
            add_camera_interactive()
            return
    
    print("=" * 50)
    print(get_translation("add_camera", "management_title"))
    print("=" * 50)
    print(f"\n{get_translation('add_camera', 'add_camera')}")
    print(get_translation("add_camera", "show_cameras"))
    print(get_translation("add_camera", "exit"))
    
    while True:
        try:
            choice = input(f"\n{get_translation('add_camera', 'choice_prompt')} ").strip()
            
            if choice == "1":
                add_camera_interactive()
                break
            elif choice == "2":
                list_cameras()
                break
            elif choice == "3":
                print(get_translation("add_camera", "goodbye"))
                break
            else:
                print(get_translation("add_camera", "invalid_choice"))
        except KeyboardInterrupt:
            print(f"\n{get_translation('add_camera', 'goodbye')}")
            break
        except Exception as e:
            print(get_translation("add_camera", "error") % str(e))

if __name__ == "__main__":
    main()
