import os
import subprocess
import logging
import psutil
import time
from pathlib import Path
import config
from telegram_notifier import send_telegram_message
from security_manager import SecurityManager
import threading
from datetime import datetime, timedelta

# ✅ Recupera REGISTRAZIONI_DIR e logga il valore
REGISTRAZIONI_DIR = config.REGISTRAZIONI_DIR
logging.info(f"📂 REGISTRAZIONI_DIR usato in process_manager.py: {REGISTRAZIONI_DIR}")

# ✅ Crea la cartella se non esiste
os.makedirs(REGISTRAZIONI_DIR, exist_ok=True)
logging.info(f"📁 Verifica cartella registrazioni: {REGISTRAZIONI_DIR} (creata se non esiste)")

# Inizializza security manager per logging sicuro
security_manager = SecurityManager(config.CONFIG_FILE)

processes = []
FFMPEG_LOG_PATH = "logs/ffmpeg_records.log"
restart_attempts = {}
last_restart_time = {}  # Traccia l'ultimo riavvio per ogni telecamera
MAX_ATTEMPTS = 5
RESTART_COOLDOWN = 300  # 5 minuti di cooldown tra riavvii per la stessa telecamera
HEALTH_CHECK_INTERVAL = 120  # Controlla la salute ogni 2 minuti (era 60)

def reset_restart_counters():
    """Reset automatico dei contatori di riavvio ogni 24 ore"""
    global restart_attempts, last_restart_time
    while True:
        time.sleep(86400)  # 24 ore
        old_attempts = restart_attempts.copy()
        restart_attempts.clear()
        last_restart_time.clear()
        if old_attempts:
            logging.info(f"🔄 Reset automatico contatori riavvio. Erano: {old_attempts}")
            send_telegram_message("🔄 Reset automatico contatori riavvio telecamere completato.")

# Avvia il thread per il reset automatico
reset_thread = threading.Thread(target=reset_restart_counters, daemon=True)
reset_thread.start()

def get_backoff_delay(attempts):
    """Calcola il ritardo con backoff esponenziale"""
    if attempts <= 1:
        return 0
    elif attempts <= 3:
        return 30  # 30 secondi
    elif attempts <= 5:
        return 60  # 1 minuto
    else:
        return 300  # 5 minuti

def is_ffmpeg_healthy(proc_info):
    """Controllo avanzato della salute del processo ffmpeg"""
    proc = proc_info["process"]
    name = proc_info["name"]

    # Controlla se il processo è ancora attivo
    if proc.poll() is not None:
        return False, "Processo terminato"

    try:
        # Controlla l'utilizzo CPU del processo
        process = psutil.Process(proc.pid)
        
        # Verifica se il processo è in stato zombie o simile
        if process.status() in [psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD]:
            return False, "Processo in stato zombie"
        
        # Controlla memoria
        memory_info = process.memory_info()
        if memory_info.rss > 1024 * 1024 * 1024:  # > 1GB
            logging.warning(f"⚠️ {name} sta usando molta memoria: {memory_info.rss / (1024**2):.1f} MB")
        
        # Verifica che il processo abbia file aperti (segno che sta leggendo/scrivendo)
        try:
            open_files = process.open_files()
            if not open_files:
                return False, "Processo senza file aperti"
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            # Se non possiamo accedere ai file aperti, assumiamo che sia OK
            pass
        
        return True, "Processo sano"
    except psutil.NoSuchProcess:
        return False, "Processo non trovato"
    except Exception as e:
        return False, f"Errore controllo salute: {e}"

def can_restart_process(name):
    """Verifica se un processo può essere riavviato (rispetta cooldown)"""
    if name in last_restart_time:
        time_since_last = datetime.now() - last_restart_time[name]
        if time_since_last.total_seconds() < RESTART_COOLDOWN:
            remaining = RESTART_COOLDOWN - time_since_last.total_seconds()
            logging.info(f"⏳ Cooldown attivo per {name}: {remaining:.0f} secondi rimanenti")
            return False
    return True

def is_ffmpeg_running(proc_info):
    """ Controlla se ffmpeg sta funzionando correttamente con controlli avanzati. """
    healthy, reason = is_ffmpeg_healthy(proc_info)
    if not healthy:
        logging.error(f"[DEBUG] {proc_info['name']}: {reason}")
        # Invia notifica Telegram solo per problemi gravi
        if reason not in ["Processo senza file aperti"]:  # Non notificare per problemi minori
            send_telegram_message(f"⚠️ {proc_info['name']}: {reason}")
    return healthy

def is_recording_active(camera_name, recordings_dir, timeout=59):
    """ Verifica se c'è un file di registrazione recente per la telecamera specificata. """
    recordings_path = Path(recordings_dir)
    pattern = f"{camera_name}_*.mkv"
    recent_files = [
        file for file in recordings_path.glob(pattern)
        if file.stat().st_mtime >= time.time() - timeout
    ]

    if recent_files:
        return True
    else:
        logging.warning(f"[DEBUG] Nessun file recente trovato per {camera_name}.")
        send_telegram_message(f"❌ File recente non trovato per {camera_name}")
        return False

def start_ffmpeg_processes(FFMPEG_COMMANDS):
    global processes
    os.makedirs(os.path.dirname(FFMPEG_LOG_PATH), exist_ok=True)

    for cmd in FFMPEG_COMMANDS:
        ffmpeg_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-use_wallclock_as_timestamps",
            "1",
            "-i",
            cmd["url"],
            "-vcodec",
            "copy",
            "-acodec",
            "copy",
            "-f",
            "segment",
            "-reset_timestamps",
            "1",
            "-segment_time",
            "300",
            "-segment_format",
            "mkv",
            "-segment_atclocktime",
            "1",
            "-strftime",
            "1",
            cmd["output"],
        ]
        # Log sicuro del comando (nasconde credenziali)
        safe_cmd = security_manager.sanitize_ffmpeg_command(ffmpeg_cmd)
        logging.info(f"Avvio ffmpeg per {cmd['name']} con comando: {' '.join(safe_cmd)}")
        
        # Genera il percorso del file log specifico per la telecamera
        camera_log_file = f"logs/ffmpeg_{cmd['name']}.log"
        os.makedirs(os.path.dirname(camera_log_file), exist_ok=True)
        
        with open(camera_log_file, "a") as log_file:
            proc = subprocess.Popen(ffmpeg_cmd, stdout=log_file, stderr=log_file)
            
            # Controllo iniziale dello stato del processo
            time.sleep(5)  # Aspetta che il processo si stabilizzi
            
            if proc.poll() is not None:
                # Processo terminato, leggi l'errore dal log
                try:
                    with open(camera_log_file, "r") as error_file:
                        error_lines = error_file.readlines()
                        if error_lines:
                            last_errors = ''.join(error_lines[-5:]).strip()  # Ultime 5 righe
                            logging.error(f"❌ Processo ffmpeg per {cmd['name']} terminato all'avvio. Errore: {last_errors}")
                            send_telegram_message(f"❌ Avvio {cmd['name']} fallito: {last_errors}")
                        else:
                            logging.error(f"❌ Processo ffmpeg per {cmd['name']} terminato all'avvio.")
                            send_telegram_message(f"❌ Avvio {cmd['name']} fallito: processo terminato immediatamente.")
                except Exception as e:
                    logging.error(f"❌ Processo ffmpeg per {cmd['name']} terminato all'avvio. Errore lettura log: {e}")
                    send_telegram_message(f"❌ Avvio {cmd['name']} fallito: processo terminato immediatamente.")
            
        processes.append({"name": cmd["name"], "process": proc, "output": cmd["output"]})

def stop_ffmpeg_processes():
    """ Termina tutti i processi ffmpeg attivi. """
    global processes
    for proc_info in processes:
        proc = proc_info["process"]
        name = proc_info["name"]
        if proc.poll() is None:
            logging.info(f"Terminazione del processo {name} (PID {proc.pid})")
            proc.terminate()
            try:
                proc.wait(timeout=10)
                logging.info(f"Processo {name} terminato correttamente.")
            except subprocess.TimeoutExpired:
                logging.warning(f"Forzatura della terminazione del processo {name} (PID {proc.pid})")
                proc.kill()
    processes.clear()

def restart_ffmpeg_process(name, FFMPEG_COMMANDS):
    """ Riavvia il processo ffmpeg con controlli avanzati e backoff esponenziale. """
    global restart_attempts, last_restart_time

    # Controlla cooldown
    if not can_restart_process(name):
        return

    if name not in restart_attempts:
        restart_attempts[name] = 0

    restart_attempts[name] += 1
    last_restart_time[name] = datetime.now()

    if restart_attempts[name] >= MAX_ATTEMPTS:
        logging.error(f"❌ Troppi riavvii per {name}, disattivato il riavvio automatico.")
        send_telegram_message(f"❌ Impossibile riavviare ffmpeg per {name}. Troppi tentativi falliti ({MAX_ATTEMPTS}).")
        restart_attempts[name] = -1  # Disabilita il riavvio per questa telecamera
        return

    # Calcola ritardo con backoff esponenziale
    delay = get_backoff_delay(restart_attempts[name])
    if delay > 0:
        logging.info(f"⏳ Attesa {delay}s prima del riavvio di {name} (tentativo {restart_attempts[name]}/{MAX_ATTEMPTS})")
        time.sleep(delay)

    for cmd in FFMPEG_COMMANDS:
        if cmd["name"] == name:
            logging.info(f"🔄 Riavvio di ffmpeg per {cmd['name']} (tentativo {restart_attempts[name]}/{MAX_ATTEMPTS})")

            # Termina il processo esistente con controlli migliorati
            for proc_info in list(processes):
                if proc_info["name"] == name:
                    proc = proc_info["process"]
                    if proc.poll() is None:
                        logging.info(f"⏹ Terminazione del processo {name} (PID {proc.pid})")
                        proc.terminate()
                        try:
                            proc.wait(timeout=15)  # Aumentato timeout
                            logging.info(f"✅ Processo {name} terminato correttamente.")
                        except subprocess.TimeoutExpired:
                            logging.warning(f"⚠️ Forzatura della terminazione del processo {name} (PID {proc.pid})")
                            proc.kill()
                            try:
                                proc.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                logging.error(f"❌ Impossibile terminare {name} (PID {proc.pid})")
                    processes.remove(proc_info)

            # Genera il percorso del file log specifico per la telecamera
            camera_log_file = f"logs/ffmpeg_{name}.log"
            os.makedirs(os.path.dirname(camera_log_file), exist_ok=True)

            # Prepara comando ffmpeg compatibile con versioni più vecchie
            ffmpeg_cmd = [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-loglevel", "error",
                "-rtsp_transport", "tcp",
                "-use_wallclock_as_timestamps", "1",
                "-i", cmd["url"],
                "-vcodec", "copy",
                "-acodec", "copy",
                "-f", "segment",
                "-reset_timestamps", "1",
                "-segment_time", "300",
                "-segment_format", "mkv",
                "-segment_atclocktime", "1",
                "-strftime", "1",
                cmd["output"],
            ]

            # Avvia il nuovo processo ffmpeg
            with open(camera_log_file, "a") as log_file:
                safe_cmd = security_manager.sanitize_ffmpeg_command(ffmpeg_cmd)
                logging.info(f"▶️ Avvio ffmpeg per {cmd['name']} con comando: {' '.join(safe_cmd)}")
                send_telegram_message(f"⚠️ Riavvio ffmpeg per {cmd['name']} ({restart_attempts[name]}/{MAX_ATTEMPTS}).")
                
                try:
                    proc = subprocess.Popen(ffmpeg_cmd, stdout=log_file, stderr=log_file)
                    
                    # Attesa e controllo iniziale
                    time.sleep(10)  # Aspetta più tempo per stabilizzazione
                    
                    if proc.poll() is None:
                        # Processo ancora attivo, controlla se sta davvero registrando
                        time.sleep(5)  # Attesa aggiuntiva
                        if is_recording_active(name, REGISTRAZIONI_DIR, timeout=30):
                            logging.info(f"✅ Processo ffmpeg per {name} avviato e registra correttamente.")
                            restart_attempts[name] = 0  # Reset conteggio errori
                            send_telegram_message(f"✅ {name} riavviato con successo e sta registrando.")
                        else:
                            logging.warning(f"⚠️ {name} avviato ma non sta registrando ancora.")
                    else:
                        # Processo terminato, leggi l'errore dal log
                        try:
                            with open(camera_log_file, "r") as error_file:
                                error_lines = error_file.readlines()
                                if error_lines:
                                    last_errors = ''.join(error_lines[-5:]).strip()  # Ultime 5 righe
                                    logging.error(f"❌ Processo ffmpeg per {name} terminato immediatamente. Errore: {last_errors}")
                                    send_telegram_message(f"❌ Riavvio {name} fallito: {last_errors}")
                                else:
                                    logging.error(f"❌ Processo ffmpeg per {name} terminato immediatamente.")
                                    send_telegram_message(f"❌ Riavvio {name} fallito: processo terminato immediatamente.")
                        except Exception as e:
                            logging.error(f"❌ Processo ffmpeg per {name} terminato immediatamente. Errore lettura log: {e}")
                            send_telegram_message(f"❌ Riavvio {name} fallito: processo terminato immediatamente.")
                    
                    processes.append({"name": cmd["name"], "process": proc, "output": cmd["output"]})
                    
                except Exception as e:
                    logging.error(f"❌ Errore nell'avvio di ffmpeg per {name}: {e}")
                    send_telegram_message(f"❌ Errore riavvio {name}: {str(e)}")
            break

def get_storage_usage_gb():
    """ Restituisce l'uso dello storage in GB con informazioni dettagliate. """
    try:
        usage = psutil.disk_usage(REGISTRAZIONI_DIR)
        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        
        # Log dettagliato solo se lo spazio è critico
        if free_gb < 50:  # Meno di 50GB liberi
            logging.warning(f"💾 Spazio disco critico: {free_gb:.1f}GB liberi su {total_gb:.1f}GB totali")
        
        return used_gb
    except Exception as e:
        logging.error(f"❌ Errore durante la lettura dello spazio su {REGISTRAZIONI_DIR}: {e}")
        return 0

def get_storage_statistics():
    """Restituisce statistiche dettagliate dello storage"""
    try:
        usage = psutil.disk_usage(REGISTRAZIONI_DIR)
        files = list(Path(REGISTRAZIONI_DIR).glob("*.mkv"))
        
        total_files = len(files)
        if total_files > 0:
            oldest_file = min(files, key=lambda f: f.stat().st_mtime)
            newest_file = max(files, key=lambda f: f.stat().st_mtime)
            avg_file_size = sum(f.stat().st_size for f in files) / total_files / (1024**2)  # MB
            
            return {
                'total_gb': usage.total / (1024 ** 3),
                'used_gb': usage.used / (1024 ** 3),
                'free_gb': usage.free / (1024 ** 3),
                'usage_percent': (usage.used / usage.total) * 100,
                'total_files': total_files,
                'oldest_file': oldest_file.name,
                'newest_file': newest_file.name,
                'avg_file_size_mb': avg_file_size
            }
    except Exception as e:
        logging.error(f"❌ Errore calcolo statistiche storage: {e}")
        return None

def smart_cleanup(path, target_free_gb=100):
    """Pulizia intelligente basata su spazio target da liberare"""
    try:
        usage = psutil.disk_usage(path)
        free_gb = usage.free / (1024 ** 3)
        
        if free_gb >= target_free_gb:
            return 0  # Nessuna pulizia necessaria
        
        files = list(Path(path).glob("*.mkv"))
        if not files:
            return 0
        
        # Ordina per data di modifica (più vecchi per primi)
        files.sort(key=lambda f: f.stat().st_mtime)
        
        deleted_count = 0
        bytes_to_free = (target_free_gb - free_gb) * (1024 ** 3)
        bytes_freed = 0
        
        for file in files:
            try:
                file_size = file.stat().st_size
                file.unlink()
                bytes_freed += file_size
                deleted_count += 1
                
                logging.info(f"🗑️ Eliminato: {file.name} ({file_size / (1024**2):.1f} MB)")
                
                if bytes_freed >= bytes_to_free:
                    break
                    
            except Exception as e:
                logging.error(f"❌ Errore eliminazione {file.name}: {e}")
        
        logging.info(f"✅ Pulizia completata: {deleted_count} file eliminati, {bytes_freed / (1024**3):.1f} GB liberati")
        send_telegram_message(f"🗑️ Pulizia automatica: {deleted_count} file eliminati, {bytes_freed / (1024**3):.1f} GB liberati")
        
        return deleted_count
        
    except Exception as e:
        logging.error(f"❌ Errore durante la pulizia intelligente: {e}")
        return 0

def delete_oldest_files(path, files_to_delete=6):
    """ Elimina i file più vecchi nella directory specificata con controlli migliorati. """
    if not os.path.isdir(path):
        logging.error(f"⚠️ Percorso non valido o inesistente: {path}")
        return 0

    files = list(Path(path).glob("*.mkv"))
    if not files:
        logging.warning("📂 Nessun file .mkv da eliminare nella directory.")
        return 0

    # Protezione: non eliminare file più recenti di 1 ora
    current_time = time.time()
    safe_files = [f for f in files if current_time - f.stat().st_mtime > 3600]
    
    if not safe_files:
        logging.warning("⚠️ Nessun file sicuro da eliminare (tutti i file sono più recenti di 1 ora)")
        return 0

    files.sort(key=lambda f: f.stat().st_mtime)
    deleted_count = 0
    
    for i in range(min(files_to_delete, len(safe_files))):
        oldest = safe_files[i]
        try:
            file_size = oldest.stat().st_size
            oldest.unlink()
            deleted_count += 1
            logging.info(f"🗑️ Eliminato: {oldest.name} ({file_size / (1024**2):.1f} MB)")
        except Exception as e:
            logging.error(f"❌ Errore nell'eliminazione del file {oldest}: {e}")
    
    return deleted_count

def system_health_check():
    """Controllo completo della salute del sistema"""
    while True:
        try:
            time.sleep(HEALTH_CHECK_INTERVAL)
            
            # Verifica risorse sistema
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_usage = psutil.disk_usage(REGISTRAZIONI_DIR)
            
            # Avvisi per risorse critiche
            if cpu_percent > 90:
                logging.warning(f"⚠️ CPU usage critico: {cpu_percent}%")
                send_telegram_message(f"⚠️ CPU usage critico: {cpu_percent}%")
            
            if memory.percent > 85:
                logging.warning(f"⚠️ Memoria critica: {memory.percent}%")
                send_telegram_message(f"⚠️ Memoria critica: {memory.percent}%")
            
            if disk_usage.percent > 95:
                logging.critical(f"🔥 Disco quasi pieno: {disk_usage.percent}%")
                send_telegram_message(f"🔥 CRITICO: Disco quasi pieno: {disk_usage.percent}%")
            
            # Verifica processi orfani ffmpeg
            ffmpeg_processes = [p for p in psutil.process_iter(['pid', 'name', 'cmdline']) 
                              if 'ffmpeg' in p.info['name'].lower()]
            
            active_pids = [proc_info["process"].pid for proc_info in processes if proc_info["process"].poll() is None]
            
            for proc in ffmpeg_processes:
                if proc.info['pid'] not in active_pids:
                    logging.warning(f"⚠️ Processo ffmpeg orfano trovato: PID {proc.info['pid']}")
                    try:
                        proc.terminate()
                        logging.info(f"✅ Processo orfano terminato: PID {proc.info['pid']}")
                    except:
                        pass
            
            # Log salute sistema (ogni 10 minuti)
            if time.time() % 600 < HEALTH_CHECK_INTERVAL:
                logging.info(f"💚 Sistema OK: CPU {cpu_percent}%, RAM {memory.percent}%, Disco {disk_usage.percent}%")
                
        except Exception as e:
            logging.error(f"❌ Errore health check: {e}")

# Avvia il thread di health check
health_thread = threading.Thread(target=system_health_check, daemon=True)
health_thread.start()

