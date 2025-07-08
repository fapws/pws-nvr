import telebot
import os
import configparser
import psutil
import time
import pathlib
import subprocess
import logging
from functools import wraps
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from config import REGISTRAZIONI_DIR, USE_EXTERNAL_DRIVE, EXTERNAL_MOUNT_POINT, unmount_hard_drive, load_camera_config, CONFIG_FILE
from secure_executor import SecureCommandExecutor
from telegram_notifier import send_telegram_message
from language_manager import init_language, get_translation
from security_manager import SecurityManager

# Inizializza il security manager per decifrare le credenziali
security_manager = SecurityManager(CONFIG_FILE)

# Legge il file di configurazione
config = configparser.RawConfigParser()
config.read(CONFIG_FILE)

# Recupera le credenziali di Telegram decifrate
token = config.get("TELEGRAM", "BOT_TOKEN", fallback=None)
if token and token.startswith('ENC:'):
    TELEGRAM_BOT_TOKEN = security_manager.decrypt_password(token[4:])
else:
    TELEGRAM_BOT_TOKEN = token

chat_id_str = config.get("TELEGRAM", "CHAT_ID", fallback="0")
if chat_id_str and chat_id_str.startswith('ENC:'):
    chat_id_str = security_manager.decrypt_password(chat_id_str[4:])

try:
    TELEGRAM_CHAT_ID = int(chat_id_str)
except ValueError:
    TELEGRAM_CHAT_ID = 0

tailscale_ip = config.get("TELEGRAM", "ip", fallback="")
if tailscale_ip and tailscale_ip.startswith('ENC:'):
    TAILSCALE_IP = security_manager.decrypt_password(tailscale_ip[4:])
else:
    TAILSCALE_IP = tailscale_ip

# Verifica che le credenziali siano valide
if not TELEGRAM_BOT_TOKEN:
    logging.error("❌ Token Telegram non trovato o non valido nel file di configurazione")
    exit(1)

if not TELEGRAM_CHAT_ID:
    logging.error("❌ Chat ID Telegram non trovato o non valido nel file di configurazione")
    exit(1)

# Inizializza il bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Inizializza secure executor
secure_executor = SecureCommandExecutor()

# Inizializza il gestore lingue (legge automaticamente da config.ini)
try:
    init_language()
except Exception as e:
    logging.error(f"Errore caricamento lingua: {e}")
    # Fallback all'inglese
    init_language("en")

def set_bot_commands():
    """Registra i comandi del bot per il menu suggerito da Telegram."""
    commands = [
        BotCommand("nvr_status", "📊 " + get_translation("bot", "nvr_status").split("*")[1].strip()),
        BotCommand("nvr_start", "▶️ " + get_translation("bot", "nvr_start").replace("...", "")),
        BotCommand("nvr_restart", "🔄 " + get_translation("bot", "nvr_restart").replace("...", "")),
        BotCommand("nvr_stop", "⏹ " + get_translation("bot", "nvr_stop").replace("...", "")),
        BotCommand("reset_camera_attempts", "🔄 " + get_translation("bot", "reset_camera_attempts").replace("...", "")),
        BotCommand("start_rtsp", "🟢 " + get_translation("bot", "start_rtsp").replace("...", "")),
        BotCommand("stop_rtsp", "🔴 " + get_translation("bot", "stop_rtsp").replace("...", "")),
        BotCommand("tailscale_start", "🟢 " + get_translation("bot", "tailscale_start").replace("...", "")),
        BotCommand("tailscale_vpn", "🟢 " + get_translation("bot", "tailscale_vpn").replace("...", "")),
        BotCommand("tailscale_stop", "🔴 " + get_translation("bot", "tailscale_stop").replace("...", "")),
        BotCommand("tailscale_status", "📡 " + get_translation("bot", "tailscale_status").split("*")[1].strip()),
        BotCommand("system_health", "💚 " + get_translation("bot", "system_health").split("*")[1].strip()),
        BotCommand("storage_stats", "💾 " + get_translation("bot", "storage_stats").split("*")[1].strip()),
        BotCommand("process_status", "⚙️ " + get_translation("bot", "process_status").split("*")[1].strip()),
        BotCommand("cleanup_storage", "🗑️ " + get_translation("bot", "cleanup_storage").replace("...", "")),
        BotCommand("reboot", "🔄 " + get_translation("bot", "reboot").replace("...", "")),
        BotCommand("shutdown", "⚡ " + get_translation("bot", "shutdown").replace("...", ""))
    ]
    try:
        # Imposta i comandi del bot tramite API
        bot.set_my_commands(commands)
        logging.info(get_translation("bot", "commands_set"))
    except Exception as e:
        logging.error(get_translation("bot", "commands_set_error", str(e)))

def authorized_only(func):
    """Decoratore per verificare se l'utente è autorizzato."""
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if message.chat.id != TELEGRAM_CHAT_ID:
            bot.reply_to(message, get_translation("bot", "access_denied"))
            return
        return func(message, *args, **kwargs)
    return wrapper

def system_recently_booted():
    """Controlla se il sistema è stato avviato da meno di 60 secondi per prevenire loop di reboot."""
    boot_time = psutil.boot_time()
    current_time = time.time()
    return (current_time - boot_time) < 60  # Controlla se è passato meno di 1 minuto dall'ultimo avvio

### GESTIONE SERVIZI SYSTEMD ###
def get_nvr_service_status():
    """Ottiene lo stato del servizio NVR systemd."""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'nvr'], 
                              capture_output=True, text=True)
        is_active = result.stdout.strip() == 'active'
        
        result = subprocess.run(['systemctl', 'is-enabled', 'nvr'], 
                              capture_output=True, text=True)
        is_enabled = result.stdout.strip() == 'enabled'
        
        return is_active, is_enabled
    except Exception as e:
        logging.error(f"Errore controllo stato servizio NVR: {e}")
        return False, False

def start_nvr_service():
    """Avvia il servizio NVR systemd."""
    try:
        result = subprocess.run(['sudo', 'systemctl', 'start', 'nvr'], 
                              capture_output=True, text=True)
        return result.returncode == 0, result.stderr
    except Exception as e:
        return False, str(e)

def stop_nvr_service():
    """Ferma il servizio NVR systemd."""
    try:
        result = subprocess.run(['sudo', 'systemctl', 'stop', 'nvr'], 
                              capture_output=True, text=True)
        return result.returncode == 0, result.stderr
    except Exception as e:
        return False, str(e)

def restart_nvr_service():
    """Riavvia il servizio NVR systemd."""
    try:
        result = subprocess.run(['sudo', 'systemctl', 'restart', 'nvr'], 
                              capture_output=True, text=True)
        return result.returncode == 0, result.stderr
    except Exception as e:
        return False, str(e)

def get_telegram_bot_service_status():
    """Ottiene lo stato del servizio Telegram Bot systemd."""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'telegram_bot'], 
                              capture_output=True, text=True)
        is_active = result.stdout.strip() == 'active'
        
        result = subprocess.run(['systemctl', 'is-enabled', 'telegram_bot'], 
                              capture_output=True, text=True)
        is_enabled = result.stdout.strip() == 'enabled'
        
        return is_active, is_enabled
    except Exception as e:
        logging.error(f"Errore controllo stato servizio Telegram Bot: {e}")
        return False, False

### COMANDI DI SISTEMA ###
@bot.message_handler(commands=['reboot'])
@authorized_only
def reboot(message):
    if system_recently_booted():
        bot.reply_to(message, get_translation("bot", "system_recently_booted"))
        return
    
    bot.reply_to(message, get_translation("bot", "rebooting"))
    time.sleep(5)  # Leggero ritardo per evitare comandi doppi
    success, msg = secure_executor.system_reboot()
    if not success:
        bot.reply_to(message, get_translation("bot", "reboot_error", msg))
        # Fallback solo in caso di emergenza
        os.system("sudo reboot")

@bot.message_handler(commands=['shutdown'])
@authorized_only
def shutdown(message):
    if system_recently_booted():
        bot.reply_to(message, get_translation("bot", "system_recently_booted"))
        return

    bot.reply_to(message, get_translation("bot", "shutting_down"))

    if unmount_hard_drive():
        bot.reply_to(message, get_translation("bot", "external_drive_unmounted"))
    else:
        bot.reply_to(message, get_translation("bot", "external_drive_unmount_error"))

    time.sleep(5)
    success, msg = secure_executor.system_shutdown()
    if not success:
        bot.reply_to(message, get_translation("bot", "shutdown_error", msg))
        # Fallback solo in caso di emergenza
        os.system("sudo shutdown -h now")

### GESTIONE SERVIZIO NVR ###
@bot.message_handler(commands=['nvr_start'])
@authorized_only
def nvr_start(message):
    success, msg = secure_executor.systemctl_service("start", "nvr")
    if success:
        bot.reply_to(message, get_translation("bot", "nvr_service_started"))
    else:
        bot.reply_to(message, get_translation("bot", "nvr_service_error", "avvio", msg))

@bot.message_handler(commands=['nvr_restart'])
@authorized_only
def nvr_restart(message):
    success, msg = secure_executor.systemctl_service("restart", "nvr")
    if success:
        bot.reply_to(message, get_translation("bot", "nvr_service_restarted"))
    else:
        bot.reply_to(message, get_translation("bot", "nvr_service_error", "riavvio", msg))

@bot.message_handler(commands=['nvr_stop'])
@authorized_only
def nvr_stop(message):
    success, msg = secure_executor.systemctl_service("stop", "nvr")
    if success:
        bot.reply_to(message, get_translation("bot", "nvr_service_stopped"))
    else:
        bot.reply_to(message, get_translation("bot", "nvr_service_error", "stop", msg))

### GESTIONE COMANDO STATUS ###
@bot.message_handler(commands=['nvr_status'])
@authorized_only
def nvr_status(message):
    # 🖥 Ottiene l'uso della CPU
    cpu_usage = psutil.cpu_percent(interval=1)

    # 💾 Ottiene la memoria disponibile e usata
    mem = psutil.virtual_memory()
    mem_total = round(mem.total / (1024 ** 2), 2)  # Converti in MB
    mem_used = round(mem.used / (1024 ** 2), 2)
    mem_percent = mem.percent

    # ⏳ Ottiene l'uptime del sistema
    uptime_formatted = os.popen("uptime -p").read().strip()

    # 🔥 Ottiene la temperatura della CPU (se disponibile)
    try:
        temps = psutil.sensors_temperatures()
        cpu_temp = temps['coretemp'][0].current  # Per CPU Intel (modifica se serve)
    except (KeyError, AttributeError):
        cpu_temp = "N/A"

    # 📟 Ottiene lo stato del servizio NVR
    success, nvr_status_raw = secure_executor.systemctl_service("is-active", "nvr")
    nvr_status = get_translation("bot", "nvr_status_active") if success and "active" in nvr_status_raw else get_translation("bot", "nvr_status_inactive")

    # 🤖 Ottiene lo stato del servizio Telegram Bot
    success, bot_status_raw = secure_executor.systemctl_service("is-active", "telegram_bot")
    bot_status = get_translation("bot", "nvr_status_active") if success and "active" in bot_status_raw else get_translation("bot", "nvr_status_inactive")

    # 📡 Ottiene lo stato di Tailscale
    success, tailscale_status_raw = secure_executor.systemctl_service("is-active", "tailscaled")
    tailscale_status = get_translation("bot", "nvr_status_connected") if success and "active" in tailscale_status_raw else get_translation("bot", "nvr_status_disconnected")

    # 🎥 Ottiene lo stato di MediaMTX (Server RTSP)
    success, rtsp_status_raw = secure_executor.systemctl_service("is-active", "mediamtx")
    rtsp_status = get_translation("bot", "nvr_status_active") if success and "active" in rtsp_status_raw else get_translation("bot", "nvr_status_inactive")

    # 📶 Ottiene l'uso della rete nell'ultimo secondo
    net1 = psutil.net_io_counters()
    time.sleep(1)  # Aspetta un secondo per calcolare la velocità effettiva
    net2 = psutil.net_io_counters()

    net_sent = round((net2.bytes_sent - net1.bytes_sent) / (1024 ** 2), 2)  # MB inviati al secondo
    net_recv = round((net2.bytes_recv - net1.bytes_recv) / (1024 ** 2), 2)  # MB ricevuti al secondo

    # 🔋 Ottiene l'uso della batteria (se applicabile)
    try:
        battery = psutil.sensors_battery()
        battery_status = f"{round(battery.percent)}% 🔋" if battery else "N/A"
    except AttributeError:
        battery_status = "N/A"

    # Costruisce il messaggio da inviare su Telegram
    status_message = (
        f"{get_translation('bot', 'nvr_status_title')}\n"
        f"{get_translation('bot', 'nvr_status_cpu', cpu_usage)}\n"
        f"{get_translation('bot', 'nvr_status_temp', cpu_temp)}\n"
        f"{get_translation('bot', 'nvr_status_ram', mem_used, mem_total, mem_percent)}\n"
        f"{get_translation('bot', 'nvr_status_service', nvr_status)}\n"
        f"🤖 Telegram Bot: {bot_status}\n"
        f"{get_translation('bot', 'nvr_status_tailscale', tailscale_status)}\n"
        f"{get_translation('bot', 'nvr_status_rtsp', rtsp_status)}\n"
        f"{get_translation('bot', 'nvr_status_network', net_sent, net_recv)}\n"
        f"{get_translation('bot', 'nvr_status_battery', battery_status)}\n"
        f"{get_translation('bot', 'nvr_status_uptime', uptime_formatted)}"
    )

    bot.send_message(TELEGRAM_CHAT_ID, status_message, parse_mode="Markdown")

### RESET CAMERAS ATTEMPTS ###
@bot.message_handler(commands=['reset_camera_attempts'])
@authorized_only
def reset_all_camera_attempts(message):
    # Questa funzionalità richiede il riavvio del servizio NVR per resettare i contatori
    success, msg = secure_executor.systemctl_service("restart", "nvr")
    if success:
        bot.reply_to(message, get_translation("bot", "nvr_service_restarted") + "\n" + 
                    get_translation("bot", "camera_reset_success", "tutte le telecamere"))
        send_telegram_message(get_translation("bot", "camera_reset_success", "tutte le telecamere"))
    else:
        bot.reply_to(message, get_translation("bot", "nvr_service_error", "riavvio", msg))


### GESTIONE MEDIA MTX ###
@bot.message_handler(commands=['start_rtsp'])
@authorized_only
def start_rtsp_server(message):
    success, msg = secure_executor.systemctl_service("start", "mediamtx")
    if success:
        bot.reply_to(message, get_translation("bot", "rtsp_server_started"))
    else:
        bot.reply_to(message, get_translation("bot", "rtsp_server_error", "avvio", msg))

@bot.message_handler(commands=['stop_rtsp'])
@authorized_only
def stop_rtsp_server(message):
    success, msg = secure_executor.systemctl_service("stop", "mediamtx")
    if success:
        bot.reply_to(message, get_translation("bot", "rtsp_server_stopped"))
    else:
        bot.reply_to(message, get_translation("bot", "rtsp_server_error", "stop", msg))

### GESTIONE TAILSCALE ###
@bot.message_handler(commands=['tailscale_start'])
@authorized_only
def tailscale_start(message):
    success1, msg1 = secure_executor.systemctl_service("start", "tailscaled")
    success2, msg2 = secure_executor.tailscale_action("up")
    if success1 and success2:
        bot.reply_to(message, get_translation("bot", "tailscale_started"))
    else:
        bot.reply_to(message, get_translation("bot", "tailscale_error", "avvio", f"{msg1}, {msg2}"))

@bot.message_handler(commands=['tailscale_vpn'])
@authorized_only
def tailscale_vpn(message):
    success1, msg1 = secure_executor.systemctl_service("start", "tailscaled")
    success2, msg2 = secure_executor.tailscale_action("up", ["--advertise-exit-node"])
    if success1 and success2:
        bot.reply_to(message, get_translation("bot", "tailscale_vpn_started"))
    else:
        bot.reply_to(message, get_translation("bot", "tailscale_error", "VPN", f"{msg1}, {msg2}"))

@bot.message_handler(commands=['tailscale_stop'])
@authorized_only
def tailscale_stop(message):
    success1, msg1 = secure_executor.tailscale_action("down")
    success2, msg2 = secure_executor.systemctl_service("stop", "tailscaled")
    if success1 and success2:
        bot.reply_to(message, get_translation("bot", "tailscale_stopped"))
    else:
        bot.reply_to(message, get_translation("bot", "tailscale_error", "stop", f"{msg1}, {msg2}"))

@bot.message_handler(commands=['tailscale_status'])
@authorized_only
def tailscale_status(message):
    success, status = secure_executor.tailscale_action("status")
    if success:
        bot.reply_to(message, get_translation("bot", "tailscale_status_result", status))
    else:
        bot.reply_to(message, get_translation("bot", "tailscale_status_error", status))

### DIAGNOSTICA DI SISTEMA ###
@bot.message_handler(commands=['system_health'])
@authorized_only
def system_health_command(message):
    """Mostra lo stato di salute del sistema"""
    try:
        # Informazioni sistema
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage(REGISTRAZIONI_DIR)
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time
        
        # Conta processi ffmpeg
        ffmpeg_count = len([p for p in psutil.process_iter(['name']) 
                           if 'ffmpeg' in p.info['name'].lower()])
        
        # Temperatura CPU
        try:
            temp_result = subprocess.run(['sensors'], capture_output=True, text=True)
            max_temp = 0
            for line in temp_result.stdout.splitlines():
                if "Core" in line and "°C" in line:
                    temp_str = line.split()[2].strip("+°C")
                    temp = float(temp_str)
                    max_temp = max(max_temp, temp)
        except:
            max_temp = 0
        
        message_text = get_translation('bot', 'system_health_title') + "\n\n"
        message_text += get_translation('bot', 'system_health_cpu', cpu_percent) + "\n"
        message_text += get_translation('bot', 'system_health_ram', memory.percent, f"{memory.used / (1024**3):.1f}", f"{memory.total / (1024**3):.1f}") + "\n"
        message_text += get_translation('bot', 'system_health_disk', disk_usage.percent, f"{disk_usage.used / (1024**3):.1f}", f"{disk_usage.total / (1024**3):.1f}") + "\n"
        message_text += get_translation('bot', 'system_health_temp', max_temp) + "\n"
        message_text += get_translation('bot', 'system_health_uptime', f"{uptime / 3600:.1f}") + "\n"
        message_text += get_translation('bot', 'system_health_ffmpeg', ffmpeg_count) + "\n\n"
        message_text += get_health_status(cpu_percent, memory.percent, disk_usage.percent, max_temp)
        
        bot.reply_to(message, message_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, get_translation("bot", "system_health_error", str(e)))

@bot.message_handler(commands=['storage_stats'])
@authorized_only
def storage_stats_command(message):
    """Mostra statistiche dettagliate dello storage"""
    try:
        import pathlib
        from pathlib import Path
        
        # Calcola statistiche storage manualmente
        usage = psutil.disk_usage(REGISTRAZIONI_DIR)
        recordings_path = Path(REGISTRAZIONI_DIR)
        files = list(recordings_path.glob("*.mkv"))
        
        total_files = len(files)
        if total_files > 0:
            oldest_file = min(files, key=lambda f: f.stat().st_mtime)
            newest_file = max(files, key=lambda f: f.stat().st_mtime)
            avg_file_size = sum(f.stat().st_size for f in files) / total_files / (1024**2)  # MB
            
            message_text = get_translation('bot', 'storage_stats_title') + "\n\n"
            message_text += get_translation('bot', 'storage_stats_space') + "\n"
            message_text += get_translation('bot', 'storage_stats_total', f"{usage.total / (1024**3):.1f}") + "\n"
            message_text += get_translation('bot', 'storage_stats_used', f"{usage.used / (1024**3):.1f}", f"{(usage.used / usage.total) * 100:.1f}") + "\n"
            message_text += get_translation('bot', 'storage_stats_free', f"{usage.free / (1024**3):.1f}") + "\n\n"
            message_text += get_translation('bot', 'storage_stats_files') + "\n"
            message_text += get_translation('bot', 'storage_stats_total_files', total_files) + "\n"
            message_text += get_translation('bot', 'storage_stats_avg_size', f"{avg_file_size:.1f}") + "\n"
            message_text += get_translation('bot', 'storage_stats_oldest', oldest_file.name) + "\n"
            message_text += get_translation('bot', 'storage_stats_newest', newest_file.name) + "\n\n"
            message_text += get_translation('bot', 'storage_stats_path', REGISTRAZIONI_DIR)
        else:
            message_text = get_translation('bot', 'storage_stats_no_files')
        
        bot.reply_to(message, message_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, get_translation("bot", "storage_stats_error", str(e)))

@bot.message_handler(commands=['process_status'])
@authorized_only
def process_status_command(message):
    """Mostra lo stato dei processi ffmpeg"""
    try:
        # Conta processi ffmpeg di sistema
        ffmpeg_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            if 'ffmpeg' in proc.info['name'].lower():
                ffmpeg_processes.append(proc.info)
        
        message_text = get_translation('bot', 'process_status_title') + "\n\n"
        message_text += get_translation('bot', 'process_status_active', len(ffmpeg_processes)) + "\n\n"
        
        if ffmpeg_processes:
            message_text += get_translation('bot', 'process_status_ffmpeg_system', len(ffmpeg_processes))
            for proc in ffmpeg_processes[:5]:  # Massimo 5 processi
                message_text += "\n" + get_translation('bot', 'process_status_ffmpeg_details', proc['pid'], f"{proc['cpu_percent']:.1f}", f"{proc['memory_percent']:.1f}")
        else:
            message_text += get_translation('bot', 'process_status_no_ffmpeg')
        
        # Stato del servizio NVR
        success, nvr_status_raw = secure_executor.systemctl_service("is-active", "nvr")
        nvr_status = get_translation("bot", "nvr_status_active") if success and "active" in nvr_status_raw else get_translation("bot", "nvr_status_inactive")
        message_text += "\n\n" + get_translation('bot', 'nvr_status_service', nvr_status)
        
        bot.reply_to(message, message_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, get_translation("bot", "process_status_error", str(e)))

@bot.message_handler(commands=['cleanup_storage'])
@authorized_only
def cleanup_storage_command(message):
    """Esegue pulizia storage manuale"""
    try:
        import process_manager
        
        # Conferma prima della pulizia
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(get_translation("bot", "cleanup_confirm_button"), callback_data="confirm_cleanup"))
        keyboard.add(InlineKeyboardButton(get_translation("bot", "cleanup_cancel_button"), callback_data="cancel_cleanup"))
        
        cleanup_message = get_translation("bot", "cleanup_confirm_title") + "\n\n" + get_translation("bot", "cleanup_confirm_text")
        bot.reply_to(message, cleanup_message, reply_markup=keyboard, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, get_translation("bot", "cleanup_storage_error", str(e)))

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_cleanup", "cancel_cleanup"])
def handle_cleanup_callback(call):
    """Gestisce la conferma pulizia storage"""
    try:
        if call.data == "confirm_cleanup":
            from pathlib import Path
            import time
            
            # Pulizia manuale semplificata
            recordings_path = Path(REGISTRAZIONI_DIR)
            files = list(recordings_path.glob("*.mkv"))
            
            if not files:
                bot.edit_message_text(get_translation("bot", "cleanup_no_files"),
                                    call.message.chat.id, call.message.message_id, parse_mode='Markdown')
                return
            
            # Ordina per data di modifica (più vecchi per primi)
            files.sort(key=lambda f: f.stat().st_mtime)
            
            # Protezione: non eliminare file più recenti di 1 ora
            current_time = time.time()
            safe_files = [f for f in files if current_time - f.stat().st_mtime > 3600]
            
            if not safe_files:
                bot.edit_message_text(get_translation("bot", "cleanup_no_safe_files"),
                                    call.message.chat.id, call.message.message_id, parse_mode='Markdown')
                return
            
            # Elimina i primi 10 file più vecchi
            deleted = 0
            for file in safe_files[:10]:
                try:
                    file.unlink()
                    deleted += 1
                except Exception as e:
                    logging.error(f"Errore eliminazione {file.name}: {e}")
            
            if deleted > 0:
                bot.edit_message_text(get_translation("bot", "cleanup_completed", deleted),
                                    call.message.chat.id, call.message.message_id, parse_mode='Markdown')
            else:
                bot.edit_message_text(get_translation("bot", "cleanup_failed"),
                                    call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(get_translation("bot", "cleanup_cancelled"),
                                call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    except Exception as e:
        bot.edit_message_text(get_translation("bot", "cleanup_error_during", str(e)),
                            call.message.chat.id, call.message.message_id)

def get_health_status(cpu, memory, disk, temp):
    """Restituisce lo stato di salute del sistema"""
    issues = []
    
    if cpu > 90:
        issues.append(get_translation("bot", "health_cpu_critical"))
    elif cpu > 70:
        issues.append(get_translation("bot", "health_cpu_high"))
    
    if memory > 90:
        issues.append(get_translation("bot", "health_ram_critical"))
    elif memory > 80:
        issues.append(get_translation("bot", "health_ram_high"))
    
    if disk > 95:
        issues.append(get_translation("bot", "health_disk_critical"))
    elif disk > 85:
        issues.append(get_translation("bot", "health_disk_high"))
    
    if temp > 85:
        issues.append(get_translation("bot", "health_temp_critical"))
    elif temp > 70:
        issues.append(get_translation("bot", "health_temp_high"))
    
    if issues:
        return get_translation("bot", "health_issues_detected") + "\n" + "\n".join(f"- {issue}" for issue in issues)
    else:
        return get_translation("bot", "health_system_ok")

### MENU COMANDI ###
@bot.message_handler(commands=['menu'])
@authorized_only
def menu(message):
    # Creazione della tastiera con i comandi cliccabili
    markup = InlineKeyboardMarkup()

    # Lista dei comandi disponibili
    commands = [
        (get_translation("bot", "menu_nvr_status"), "nvr_status"),
        (get_translation("bot", "menu_nvr_start"), "nvr_start"),
        (get_translation("bot", "menu_nvr_restart"), "nvr_restart"),
        (get_translation("bot", "menu_nvr_stop"), "nvr_stop"),
        (get_translation("bot", "menu_reset_cameras"), "reset_camera_attempts"),
        (get_translation("bot", "menu_start_rtsp"), "start_rtsp"),
        (get_translation("bot", "menu_stop_rtsp"), "stop_rtsp"),
        (get_translation("bot", "menu_tailscale_start"), "tailscale_start"),
        (get_translation("bot", "menu_tailscale_vpn"), "tailscale_vpn"),
        (get_translation("bot", "menu_tailscale_stop"), "tailscale_stop"),
        (get_translation("bot", "menu_tailscale_status"), "tailscale_status"),
        (get_translation("bot", "menu_system_health"), "system_health"),
        (get_translation("bot", "menu_storage_stats"), "storage_stats"),
        (get_translation("bot", "menu_process_status"), "process_status"),
        (get_translation("bot", "menu_cleanup_storage"), "cleanup_storage"),
        (get_translation("bot", "menu_reboot"), "reboot"),
        (get_translation("bot", "menu_shutdown"), "shutdown"),
    ]

    # Aggiunge ogni comando come pulsante cliccabile
    for label, command in commands:
        markup.add(InlineKeyboardButton(label, callback_data=command))

    # Invia il messaggio con i pulsanti
    bot.send_message(TELEGRAM_CHAT_ID, get_translation("bot", "command_menu"), reply_markup=markup, parse_mode="Markdown")

# Configura il menu comandi nel bottone blu di Telegram
set_bot_commands()

# Avvia il polling per ricevere i comandi
bot.polling(none_stop=True, interval=2)
