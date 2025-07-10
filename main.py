import os
import sys
import config
import signal
import logging
import threading
import time
import psutil
import subprocess
import process_manager
from config import load_camera_config, load_logging_config, CONFIG_FILE, REGISTRAZIONI_DIR, STORAGE_SIZE, STORAGE_MAX_USE, USE_EXTERNAL_DRIVE, EXTERNAL_MOUNT_POINT, EXTERNAL_DEVICE
from logging_setup import setup_logging
from process_manager import is_recording_active
from telegram_notifier import send_telegram_message
from secure_executor import SecureCommandExecutor
from multilingual_logging import setup_multilingual_logging

# Configura il logging multilingua
setup_multilingual_logging()

STORAGE_SIZE = config.config.getint("STORAGE", "STORAGE_SIZE", fallback=450)
STORAGE_MAX_USE = config.config.getfloat("STORAGE", "STORAGE_MAX_USE", fallback=0.90)

# Inizializza l'executor sicuro
secure_executor = SecureCommandExecutor()

print(f"✅ STORAGE_SIZE aggiornato in main.py: {STORAGE_SIZE}")
print(f"✅ STORAGE_MAX_USE aggiornato in main.py: {STORAGE_MAX_USE}")

def signal_handler(sig=None, frame=None):
    logging.info("log:logs.interrupt_signal")
    send_telegram_message("⏹️ Arresto del sistema NVR.")
    process_manager.stop_ffmpeg_processes()
    sys.exit(0)

def get_disk_total_gb(path):
    """ Restituisce la dimensione totale del disco in GB, con fallback da config.ini """
    try:
        usage = psutil.disk_usage(path)
        return round(usage.total / (1024 ** 3))  # Converti in GB e arrotonda all'unità
    except Exception as e:
        logging.error(f"log:logs.disk_error:{path}:{e}")
        return STORAGE_SIZE  # Usa il valore di fallback da config.ini

def monitor_storage_and_processes(FFMPEG_COMMANDS):
    MAX_STORAGE_GB = get_disk_total_gb(REGISTRAZIONI_DIR)
    logging.info(f"log:logs.disk_size_detected:{MAX_STORAGE_GB}")
    
    # Contatori per statistiche
    storage_alerts = 0
    process_restarts = 0
    last_stats_report = time.time()
    
    time.sleep(30)  # Ritardo iniziale per dare tempo a ffmpeg di avviarsi

    while True:
        try:
            # Monitoraggio storage migliorato
            used_gb = process_manager.get_storage_usage_gb()
            usage_percent = (used_gb / MAX_STORAGE_GB) * 100
            
            # Debug ogni minuto del controllo storage
            if int(time.time()) % 60 == 0:  # Una volta al minuto
                logging.info(f"🔍 Storage check: {used_gb:.1f}GB/{MAX_STORAGE_GB}GB ({usage_percent:.1f}%) - Soglia: {MAX_STORAGE_GB * STORAGE_MAX_USE:.1f}GB")
            
            # Avviso preventivo al 80%
            if usage_percent >= 80 and storage_alerts == 0:
                logging.warning(f"log:logs.disk_space_warning:{usage_percent:.1f}")
                send_telegram_message(f"⚠️ Spazio disco al {usage_percent:.1f}% - Considerare una pulizia manuale")
                storage_alerts = 1
            
            # Pulizia automatica avanzata con debug
            storage_threshold_gb = MAX_STORAGE_GB * STORAGE_MAX_USE
            logging.debug(f"🔍 Debug pulizia: usati={used_gb:.1f}GB, soglia={storage_threshold_gb:.1f}GB, percentuale={usage_percent:.1f}%")
            
            if used_gb >= storage_threshold_gb:
                logging.warning(f"🚨 SOGLIA SUPERATA! Avvio pulizia automatica - Usati: {used_gb:.1f}GB >= Soglia: {storage_threshold_gb:.1f}GB ({usage_percent:.1f}%)")
                logging.warning(f"log:logs.disk_space_critical:{usage_percent:.1f}")
                try:
                    # Usa pulizia intelligente basata su percentuale
                    # Target: ridurre al 90% se la soglia STORAGE_MAX_USE è superata
                    target_percent = min(90, STORAGE_MAX_USE * 100 - 5)  # 5% sotto la soglia di trigger
                    deleted = process_manager.smart_cleanup(REGISTRAZIONI_DIR, target_usage_percent=target_percent)
                    if deleted > 0:
                        storage_alerts = 0  # Reset avvisi dopo pulizia
                        # Riconteggia lo spazio dopo la pulizia
                        new_used_gb = process_manager.get_storage_usage_gb()
                        new_usage_percent = (new_used_gb / MAX_STORAGE_GB) * 100
                        logging.info(f"📊 Spazio post-pulizia: {new_usage_percent:.1f}%")
                    else:
                        logging.error("log:logs.auto_cleanup_failed")
                        send_telegram_message("❌ Pulizia automatica fallita - Intervento manuale necessario")
                except Exception as e:
                    logging.error(f"log:logs.cleanup_error:{e}")
                    # Fallback alla pulizia classica
                    process_manager.delete_oldest_files(REGISTRAZIONI_DIR, files_to_delete=10)

            # Monitoraggio processi migliorato con intervalli più intelligenti
            healthy_processes = 0
            for proc_info in list(process_manager.processes):
                name = proc_info["name"]

                # Controllo salute avanzato (meno aggressivo)
                if not process_manager.is_ffmpeg_running(proc_info):
                    logging.error(f"log:logs.ffmpeg_abnormal:{name}")
                    process_manager.processes.remove(proc_info)
                    process_manager.restart_ffmpeg_process(name, FFMPEG_COMMANDS)
                    process_restarts += 1
                    continue

                healthy_processes += 1

            # Controllo registrazione attiva solo ogni 5 minuti per evitare interferenze
            current_time = time.time()
            if not hasattr(monitor_storage_and_processes, 'last_recording_check'):
                monitor_storage_and_processes.last_recording_check = current_time
            
            if current_time - monitor_storage_and_processes.last_recording_check >= 300:  # 5 minuti
                for proc_info in list(process_manager.processes):
                    name = proc_info["name"]
                    if not is_recording_active(name, REGISTRAZIONI_DIR, timeout=120):  # Timeout più lungo
                        logging.warning(f"log:logs.recording_inactive:{name}")
                        send_telegram_message(f"⚠️ Registrazione non attiva per {name}, riavvio in corso...")
                        process_manager.processes.remove(proc_info)
                        process_manager.restart_ffmpeg_process(name, FFMPEG_COMMANDS)
                        process_restarts += 1
                monitor_storage_and_processes.last_recording_check = current_time

            # Report statistiche ogni ora
            if time.time() - last_stats_report >= 3600:  # 1 ora
                stats = process_manager.get_storage_statistics()
                if stats:
                    logging.info(f"📊 Statistiche orarie: {stats['total_files']} file, {stats['used_gb']:.1f}GB usati, {healthy_processes} telecamere attive")
                    send_telegram_message(f"📊 Report NVR: {stats['total_files']} file, {stats['used_gb']:.1f}GB usati, {healthy_processes} telecamere attive, {process_restarts} riavvii")
                    process_restarts = 0  # Reset contatore
                last_stats_report = time.time()

            time.sleep(60)  # Aumentato da 20 a 60 secondi per essere meno invasivo

        except Exception as e:
            logging.error(f"❌ Errore nel ciclo monitor_storage_and_processes: {e}")
            time.sleep(10)  # Attesa più lunga in caso di errore per evitare spam

def monitor_temperature():
    alert_sent = False  # Flag per evitare notifiche ripetute
    high_temp_count = 0  # Contatore per temperature elevate consecutive
    while True:
        try:
            result = subprocess.run(["sensors"], capture_output=True, text=True, check=True)
            max_temp = 0
            for line in result.stdout.splitlines():
                if "Core" in line and "°C" in line:
                    temp_str = line.split()[2].strip("+°C")
                    temp = float(temp_str)
                    max_temp = max(max_temp, temp)

            # Usa la temperatura massima tra tutti i core
            if max_temp > 0:
                temp = max_temp
                
                # Se la temperatura supera 55°, invia una notifica (una sola volta finché non scende sotto 55)
                if temp > 54.0 and not alert_sent:
                    send_telegram_message(f"⚠️ Attenzione: la temperatura della CPU ha superato i 55C! ({temp}°C)")
                    alert_sent = True  # Evita di inviare più notifiche finché la temperatura non scende

                # Se supera 85°, incrementa il contatore
                if temp > 85.0:
                    high_temp_count += 1
                    logging.warning(f"Temperatura elevata rilevata: {temp}°C (conteggio: {high_temp_count}/3)")
                    
                    # Spegni solo dopo 3 letture consecutive sopra 85°
                    if high_temp_count >= 3:
                        logging.critical(f"Temperatura critica della CPU rilevata: {temp}°C. Spegnimento del sistema.")
                        send_telegram_message(f"🔥 Allarme critico! La CPU ha raggiunto {temp}°C per 3 volte consecutive. Arresto immediato!")
                        success, msg = secure_executor.system_shutdown()
                        if not success:
                            logging.error(f"Errore durante lo spegnimento sicuro: {msg}")
                            # Fallback solo in caso di emergenza
                            subprocess.run(["/sbin/shutdown", "now"], check=False)
                else:
                    # Reset del contatore se la temperatura scende
                    high_temp_count = 0

                # ✅ Se la temperatura torna sotto i 60°, resetta il flag per poter inviare di nuovo la notifica
                if temp <= 53.0 and alert_sent:
                    send_telegram_message(f"✅ Temperatura rientrata nella norma: {temp}°C. Il sistema è stabile.")
                    alert_sent = False

        except Exception as e:
            logging.error(f"Errore durante il monitoraggio della temperatura: {e}")

        time.sleep(30)  # Controlla la temperatura ogni 30 secondi

def mount_hard_drive():
    if USE_EXTERNAL_DRIVE:
        mount_point = EXTERNAL_MOUNT_POINT
        device = EXTERNAL_DEVICE

        if not os.path.ismount(mount_point):
            logging.info(f"Il disco esterno non è montato. Tentativo di montare {device} su {mount_point}.")
            try:
                os.makedirs(mount_point, exist_ok=True)

                # Monta il disco usando il secure executor
                success, msg = secure_executor.mount_disk(device, mount_point, 'ext4')
                if not success:
                    raise Exception(f"Errore mount: {msg}")

                # Imposta i permessi corretti per garantire che ffmpeg possa scrivere
                success, msg = secure_executor.set_ownership(mount_point, "lenonvr", recursive=True)
                if not success:
                    logging.warning(f"Errore impostazione proprietario: {msg}")

                success, msg = secure_executor.set_permissions(mount_point, "775", recursive=True)
                if not success:
                    logging.warning(f"Errore impostazione permessi: {msg}")

                logging.info("✅ Disco esterno montato con successo con EXT4.")
            except Exception as e:
                logging.critical(f"❌ Errore durante il montaggio del disco esterno: {e}")
                sys.exit(1)
        else:
            logging.info(f"✅ Il disco esterno è già montato su {mount_point}.")
    else:
        logging.info("📂 Uso del disco interno per le registrazioni. Nessun montaggio necessario.")

def main():
    # Monta il disco esterno se necessario
    mount_hard_drive()

    # Aggiungi un ritardo per assicurarti che il disco sia pronto
    logging.info("Attesa di 5 secondi per garantire che il disco sia pronto...")
    time.sleep(5)

    # Carica la configurazione dei log
    log_dir = load_logging_config(CONFIG_FILE)
    LOG_FILE = setup_logging(log_dir)

    # Carica la configurazione delle telecamere
    FFMPEG_COMMANDS = load_camera_config(CONFIG_FILE)

    # Gestione dei segnali per chiudere i processi ffmpeg correttamente
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Avvia la registrazione direttamente
    logging.info("Avvio delle registrazioni...")
    send_telegram_message("📹 Avvio delle registrazioni NVR.")
    process_manager.start_ffmpeg_processes(FFMPEG_COMMANDS)

    # Avvia il thread per monitorare lo spazio su disco e i processi
    monitor_thread = threading.Thread(target=monitor_storage_and_processes, args=(FFMPEG_COMMANDS,), daemon=True)
    monitor_thread.start()

    # Avvia il thread per monitorare la temperatura della CPU senza log in terminale
    temp_monitor_thread = threading.Thread(target=monitor_temperature, daemon=True)
    temp_monitor_thread.start()

    # Mantieni il programma in esecuzione
    try:
        signal.pause()  # Attende segnali per terminare il processo
    except KeyboardInterrupt:
        signal_handler()

if __name__ == "__main__":
    main()
