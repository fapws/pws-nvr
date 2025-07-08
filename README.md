# 🎥 Sistema NVR Universale

Un sistema di videosorveglianza (NVR) sicuro, modulare e multilingua per la gestione di telecamere IP con supporto RTSP. Controllo completo via Telegram e gestione automatica dei processi.

## 🌟 Caratteristiche Principali

### 🔒 **Sicurezza Avanzata**
- **Credenziali cifrate** con AES-256-CBC
- **Secure Command Executor** per comandi di sistema validati
- **Validazione input** completa e sanitizzazione percorsi
- **Logging sicuro** senza esposizione credenziali
- **Gestione sicura processi** e operazioni privilegiate

### 🌐 **Sistema Multilingua**
- **Supporto completo** Italiano e Inglese
- **Localizzazione** di tutti i messaggi (bot, log, interfacce)
- **Configurazione lingua** persistente
- **File traduzioni** facilmente estendibili (`lang/it.json`, `lang/en.json`)

### 📱 **Controllo Telegram Avanzato**
- **Bot Telegram** con menu interattivo
- **Comandi vocali** e tastiera personalizzata
- **Notifiche real-time** per eventi critici
- **Monitoraggio sistema** completo (CPU, RAM, temperatura, storage)
- **Controllo servizi** (NVR, Telegram Bot, Tailscale, MediaMTX)
- **Gestione storage** con pulizia manuale e automatica
- **Diagnostica avanzata** processi ffmpeg

### 💾 **Gestione Storage Intelligente**
- **Supporto multi-storage**: disco esterno, locale, percorso personalizzato
- **Mount automatico** dischi esterni con EXT4
- **Pulizia automatica** file vecchi quando spazio critico
- **Monitoraggio spazio** con soglie configurabili
- **Statistiche dettagliate** storage via Telegram

### 🎥 **Sistema di Registrazione Robusto**
- **Segmentazione video** intelligente (5 minuti per file)
- **Codec copy** per prestazioni ottimali
- **Riavvio automatico** processi ffmpeg con cooldown
- **Gestione errori avanzata** con logging dettagliato
- **Supporto stream multipli** (primario/secondario)
- **Test connessione** robusto con fallback

### ⚙️ **Servizi Systemd Separati**
- **Servizio NVR principale** (`nvr.service`)
- **Servizio Telegram Bot** (`telegram_bot.service`)
- **Gestione indipendente** e monitoraggio separato
- **Auto-restart** e logging systemd

## 🚀 Installazione Rapida

```bash
# Clona il repository
git clone https://github.com/fapws/pws-nvr.git
cd pws-nvr

# Esegui l'installazione guidata
chmod +x install.sh
./install.sh
```

Lo script di installazione gestirà automaticamente:
- ✅ Installazione Python3, ffmpeg e dipendenze
- ✅ Creazione ambiente virtuale
- ✅ **Selezione lingua** (Italiano/Inglese)
- ✅ Configurazione storage (locale/esterno/personalizzato)
- ✅ Configurazione Telegram con test
- ✅ **Configurazione telecamere manuale** con test connessione
- ✅ Cifratura automatica credenziali
- ✅ Installazione **servizi systemd separati**

> **📌 Nota**: Tailscale e MediaMTX sono servizi **opzionali** per accesso remoto e devono essere configurati separatamente. Vedi sezione [Configurazione Servizi Opzionali](#-configurazione-servizi-opzionali).

## 🛠️ Gestione Sistema

### **Prima installazione**
```bash
./install.sh
```

### **Aggiunta telecamere post-installazione**
```bash
# Attiva ambiente virtuale e aggiungi telecamera
source venv/bin/activate
python3 add_camera.py

# Oppure usa lo script wrapper
./add_camera.sh  # Gestisce automaticamente il venv
```

### **Riconfigurazione sistema**
```bash
source venv/bin/activate
python3 configure.py
```

### **Gestione servizi**
```bash
# Avvio/stop servizi separati
sudo systemctl start nvr               # Solo sistema NVR
sudo systemctl start telegram_bot      # Solo bot Telegram

# Stato servizi
sudo systemctl status nvr telegram_bot

# Abilitazione avvio automatico
sudo systemctl enable nvr telegram_bot

# Log servizi
sudo journalctl -u nvr -f             # Log NVR
sudo journalctl -u telegram_bot -f    # Log Telegram Bot
```

## 📱 Comandi Telegram Completi

### **Comandi Principali**
- `/nvr_status` - 📊 Stato completo sistema (CPU, RAM, servizi, rete)
- `/nvr_start` - ▶️ Avvia servizio NVR
- `/nvr_restart` - 🔄 Riavvia servizio NVR
- `/nvr_stop` - ⏹ Ferma servizio NVR
- `/reset_camera_attempts` - 🔄 Reset contatori riconnessione telecamere

### **Gestione Sistema**
- `/system_health` - 💚 Diagnostica completa sistema
- `/storage_stats` - 💾 Statistiche dettagliate storage
- `/process_status` - ⚙️ Stato processi ffmpeg
- `/cleanup_storage` - 🗑️ Pulizia manuale storage
- `/reboot` - 🔄 Riavvia sistema
- `/shutdown` - ⚡ Spegni sistema

### **Servizi Aggiuntivi** *(richiedono configurazione separata)*
- `/start_rtsp` - 🟢 Avvia server RTSP (MediaMTX) *
- `/stop_rtsp` - 🔴 Ferma server RTSP (MediaMTX) *
- `/tailscale_start` - 🟢 Avvia Tailscale *
- `/tailscale_vpn` - 🟢 Avvia Tailscale VPN (exit node) *
- `/tailscale_stop` - 🔴 Ferma Tailscale *
- `/tailscale_status` - 📡 Stato Tailscale *

> **📌 Nota**: I comandi contrassegnati con * richiedono l'installazione e configurazione separata dei rispettivi servizi. Vedi [Configurazione Servizi Opzionali](#-configurazione-servizi-opzionali).

### **Menu Interattivo**
- `/menu` - 📌 Menu con pulsanti interattivi per tutti i comandi

## 📁 Struttura Directory

```
nvr/
├── install.sh              # Script installazione guidata multilingua
├── add_camera.py           # Script aggiunta telecamere post-installazione
├── add_camera.sh           # Wrapper script per add_camera.py
├── configure.py            # Configuratore interattivo
├── main.py                 # Applicazione NVR principale
├── telegram_bot.py         # Bot Telegram con controllo completo
├── telegram_notifier.py    # Servizio notifiche
├── config.py               # Gestione configurazione e storage
├── process_manager.py      # Gestione processi ffmpeg avanzata
├── security_manager.py     # Cifratura/decifratura credenziali
├── secure_executor.py      # Esecuzione sicura comandi sistema
├── language_manager.py     # Gestione localizzazione
├── multilingual_logging.py # Logging multilingua
├── config.ini              # Configurazione sistema (credenziali cifrate)
├── config.ini.example      # Esempio configurazione
├── .nvr_key               # Chiave cifratura (generata automaticamente)
├── requirements.txt        # Dipendenze Python
├── venv/                  # Ambiente virtuale Python
├── logs/                  # File di log
│   ├── nvr.log           # Log principale sistema
│   ├── telegram_bot.log  # Log bot Telegram
│   └── ffmpeg_*.log      # Log specifici per telecamera
├── registrazioni/         # Video registrati (segmentati in file 5min)
└── lang/                  # File traduzioni
    ├── it.json           # Traduzioni italiano
    └── en.json           # Traduzioni inglese
```

## 🌐 Configurazione Multilingua

Il sistema supporta completamente **Italiano** e **Inglese**:

### **Selezione lingua durante installazione**
```bash
./install.sh
# Il sistema chiederà di scegliere la lingua
# La scelta viene salvata in config.ini
```

### **Cambio lingua post-installazione**
```bash
# Modifica manuale in config.ini
[LANGUAGE]
language = it  # o 'en' per inglese

# Riavvia i servizi per applicare
sudo systemctl restart nvr telegram_bot
```

### **File di traduzione personalizzati**
- `lang/it.json` - Tutte le traduzioni italiane
- `lang/en.json` - Tutte le traduzioni inglesi
- Facilmente estendibili per nuove lingue

## 🔧 Configurazione Avanzata

### **Gestione Telecamere**

#### **Configurazione manuale telecamere**
Durante l'installazione o tramite script dedicato:
```bash
# Durante installazione
./install.sh  # Include configurazione telecamere

# Post-installazione
source venv/bin/activate
python3 add_camera.py

# Con script wrapper (raccomandato)
./add_camera.sh
```

**Funzionalità script aggiunta telecamere:**
- 🔍 **Test connessione robusto** con ffprobe
- 🔒 **Cifratura automatica password** (username rimane in chiaro)
- 🌐 **Interfaccia multilingua**
- ⚡ **Diagnostica connessione** avanzata
- 🔄 **Riavvio automatico servizio** (opzionale)

#### **Configurazione esempio telecamera**
```ini
[TelecameraSoggiorno]
ip = 192.168.1.100
port = 554
path = stream1                    # Stream principale
path2 = stream2                   # Stream secondario (opzionale)
username = admin                  # Username in chiaro
password = ENC:xyz123...          # Password cifrata automaticamente
```

### **Storage Configuration**

#### **Disco esterno con mount automatico**
```ini
[STORAGE]
use_external_drive = true
external_device = /dev/sdb1
external_mount_point = /media/TOSHIBA
rec_folder_name = registrazioni
storage_size = 450               # GB
storage_max_use = 0.945          # 94.5% soglia pulizia
```

#### **Cartella locale**
```ini
[STORAGE]
use_external_drive = false
rec_folder_name = registrazioni
storage_size = 100
storage_max_use = 0.85
```

#### **Percorso personalizzato**
```ini
[STORAGE]
use_external_drive = false
custom_path = /mnt/nas/registrazioni
storage_size = 1000
storage_max_use = 0.90
```

### **Configurazione Telegram Bot**
1. Crea un bot con [@BotFather](https://t.me/BotFather)
2. Ottieni il token del bot  
3. Ottieni il tuo Chat ID da [@userinfobot](https://t.me/userinfobot)
4. Configura durante l'installazione o manualmente:

```ini
[TELEGRAM]
bot_token = ENC:token_cifrato...     # Token bot cifrato automaticamente
chat_id = 123456789                  # Chat ID (può essere cifrato)
ip = 100.64.0.1                     # IP Tailscale per streaming (opzionale)
```

### **Sicurezza e Cifratura**

#### **Cifratura automatica credenziali**
- **Password telecamere** cifrate automaticamente
- **Token Telegram** cifrato automaticamente  
- **Chiave AES-256-CBC** generata automaticamente
- **File .nvr_key** con permessi sicuri (600)

#### **Variabili d'ambiente per sicurezza avanzata**
```bash
# Chiave master personalizzata
export NVR_MASTER_PASSWORD="password_sicura_2025"

# Percorso chiave di cifratura personalizzato
export NVR_KEY_PATH="/percorso/sicuro/.nvr_key"
```

#### **Migrazione credenziali esistenti**
```bash
# Se hai credenziali non cifrate da migrare
source venv/bin/activate
python3 -c "from security_manager import SecurityManager; SecurityManager('config.ini').encrypt_existing_credentials()"
```

## 🌐 Configurazione Servizi Opzionali

> **⚠️ Importante**: I servizi seguenti sono **opzionali** e **non vengono configurati** dallo script di installazione automatica. Sono necessari solo per funzionalità avanzate di accesso remoto.

### **🔗 Tailscale (Accesso Remoto VPN)**

Tailscale permette l'accesso remoto sicuro al sistema NVR da qualsiasi luogo.

#### **Installazione Tailscale**
```bash
# Ubuntu/Debian
curl -fsSL https://tailscale.com/install.sh | sh

# Fedora/CentOS
sudo dnf config-manager --add-repo https://pkgs.tailscale.com/stable/fedora/tailscale.repo
sudo dnf install tailscale

# Arch Linux
sudo pacman -S tailscale
```

#### **Configurazione Tailscale**
```bash
# Avvia servizio
sudo systemctl enable --now tailscaled

# Connetti dispositivo
sudo tailscale up

# Per funzionalità VPN completa (exit node)
sudo tailscale up --advertise-exit-node

# Verifica stato
tailscale status
```

#### **Configurazione IP Tailscale nel bot**
Una volta configurato Tailscale, aggiorna `config.ini`:
```ini
[TELEGRAM]
ip = 100.64.0.X  # Sostituisci con il tuo IP Tailscale
```

### **📺 MediaMTX (Server RTSP per Streaming)**

MediaMTX permette di redistribuire i stream delle telecamere per accesso remoto ottimizzato.

#### **Installazione MediaMTX**
```bash
# Scarica ultima versione (verifica su GitHub per versione aggiornata)
wget https://github.com/bluenviron/mediamtx/releases/latest/download/mediamtx_v1.0.0_linux_amd64.tar.gz

# Estrai
tar -xzf mediamtx_*.tar.gz

# Sposta in directory sistema
sudo mv mediamtx /usr/local/bin/
sudo chmod +x /usr/local/bin/mediamtx

# Crea directory configurazione
sudo mkdir -p /etc/mediamtx
```

#### **Configurazione MediaMTX**
```bash
# Crea file configurazione base
sudo tee /etc/mediamtx/mediamtx.yml > /dev/null << 'EOF'
# Configurazione MediaMTX per NVR
logLevel: info
logDestinations: [stdout]
logFile: /var/log/mediamtx.log

# Server RTSP
rtspAddress: :8554
rtspEncryption: no
rtspAllowOrigin: '*'

# Autenticazione (opzionale)
authMethods: [basic]

# Path per telecamere (personalizza secondo le tue telecamere)
paths:
  camera1:
    source: rtsp://username:password@192.168.1.100:554/stream1
    sourceProtocol: automatic
    
  camera2:
    source: rtsp://username:password@192.168.1.101:554/stream1
    sourceProtocol: automatic
EOF
```

#### **Servizio systemd per MediaMTX**
```bash
# Crea servizio systemd
sudo tee /etc/systemd/system/mediamtx.service > /dev/null << 'EOF'
[Unit]
Description=MediaMTX RTSP Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/mediamtx /etc/mediamtx/mediamtx.yml
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Abilita e avvia servizio
sudo systemctl daemon-reload
sudo systemctl enable mediamtx
sudo systemctl start mediamtx
sudo systemctl status mediamtx
```

#### **Test MediaMTX**
```bash
# Testa stream locale
ffplay rtsp://localhost:8554/camera1

# Testa da remoto (con Tailscale)
ffplay rtsp://TUO_IP_TAILSCALE:8554/camera1
```

### **🔧 Configurazione Avanzata Servizi Opzionali**

#### **Firewall per Tailscale e MediaMTX**
```bash
# UFW (Ubuntu/Debian)
sudo ufw allow in on tailscale0
sudo ufw allow 8554/tcp  # MediaMTX RTSP

# iptables (manuale)
sudo iptables -A INPUT -i tailscale0 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8554 -j ACCEPT
```

#### **Monitoraggio servizi opzionali**
Dopo la configurazione, i comandi Telegram funzioneranno:
- `/tailscale_status` - Stato Tailscale
- `/tailscale_start` - Avvia Tailscale
- `/tailscale_stop` - Ferma Tailscale
- `/start_rtsp` - Avvia MediaMTX
- `/stop_rtsp` - Ferma MediaMTX

### **🎯 Casi d'uso servizi opzionali**

#### **Solo accesso locale**
- ❌ Tailscale non necessario
- ❌ MediaMTX non necessario
- ✅ Bot Telegram locale funziona perfettamente

#### **Accesso remoto via Telegram**
- ✅ Tailscale necessario per bot Telegram remoto
- ❌ MediaMTX opzionale

#### **Streaming remoto telecamere**
- ✅ Tailscale necessario
- ✅ MediaMTX necessario per stream ottimizzati
- 🎥 Accesso a stream: `rtsp://IP_TAILSCALE:8554/camera1`

#### **Setup completo remoto**
- ✅ Tailscale per accesso VPN sicuro
- ✅ MediaMTX per streaming ottimizzato
- 📱 Controllo completo via Telegram da ovunque
- 🎥 Visualizzazione stream da app RTSP remote

## 📱 Comandi Telegram Completi

Una volta configurato il bot, potrai controllare completamente il sistema via Telegram:

### **Comandi Principali**
- `/nvr_status` - 📊 Stato completo sistema (CPU, RAM, servizi, rete)
- `/nvr_start` - ▶️ Avvia servizio NVR
- `/nvr_restart` - 🔄 Riavvia servizio NVR
- `/nvr_stop` - ⏹ Ferma servizio NVR
- `/reset_camera_attempts` - 🔄 Reset contatori riconnessione telecamere

### **Gestione Sistema**
- `/system_health` - 💚 Diagnostica completa sistema
- `/storage_stats` - 💾 Statistiche dettagliate storage
- `/process_status` - ⚙️ Stato processi ffmpeg
- `/cleanup_storage` - 🗑️ Pulizia manuale storage
- `/reboot` - 🔄 Riavvia sistema
- `/shutdown` - ⚡ Spegni sistema

### **Servizi Aggiuntivi**
- `/start_rtsp` - 🟢 Avvia server RTSP (MediaMTX)
- `/stop_rtsp` - 🔴 Ferma server RTSP
- `/tailscale_start` - 🟢 Avvia Tailscale
- `/tailscale_vpn` - 🟢 Avvia Tailscale VPN (exit node)
- `/tailscale_stop` - 🔴 Ferma Tailscale
- `/tailscale_status` - 📡 Stato Tailscale

### **Menu Interattivo**
- `/menu` - 📌 Menu con pulsanti interattivi per tutti i comandi

### **Notifiche Automatiche**
Il bot invia notifiche automatiche per:
- 🚨 **Eventi critici** (spazio disco, temperatura)
- 🔄 **Riavvii automatici** processi ffmpeg
- ⚠️ **Errori connessione** telecamere
- 🟢 **Ripristino connessioni** telecamere
- 🌡️ **Temperature elevate** CPU

## 🔍 Monitoraggio Avanzato

Il sistema monitora automaticamente e intelligentemente:

### **Monitoraggio Storage**
- **Spazio disco** con pulizia automatica a soglie configurabili
- **Statistiche dettagliate** accessibili via Telegram
- **Pulizia intelligente** file più vecchi per liberare spazio
- **Protezione file recenti** (non elimina file < 1 ora)

### **Monitoraggio Sistema**
- **Temperatura CPU** con shutdown automatico di sicurezza (>85°C)
- **Uso memoria** e CPU con soglie di allarme
- **Stato servizi** systemd (NVR, Telegram Bot, Tailscale, MediaMTX)
- **Processi ffmpeg** con diagnostica avanzata

### **Monitoraggio Processi ffmpeg**
- **Riavvio automatico** con cooldown intelligente
- **Contatori riavvii** con disabilitazione automatica (max 5 tentativi)
- **Logging dettagliato** errori specifici per telecamera
- **Reset automatico** contatori ogni 24 ore

### **Gestione Connessione Telecamere**
- **Test connessione** robusto durante configurazione
- **Rilevamento disconnessioni** e riconnessione automatica
- **Fallback stream** (da primario a secondario se configurato)
- **Notifiche Telegram** per stato connessioni

## 🆘 Risoluzione Problemi

### **Errori comuni**

#### "Bot Telegram mostra servizi 'Fermi'"
```bash
# Verifica stato reale servizi
systemctl status nvr telegram_bot

# Riavvia bot Telegram
sudo systemctl restart telegram_bot

# Verifica configurazione secure_executor
tail -f logs/telegram_bot.log
```

#### "Errore test connessione telecamera (stimeout/timeout)"
Il sistema usa automaticamente l'opzione corretta per la tua versione ffprobe:
```bash
# Testa manualmente connessione
ffprobe -timeout 10000000 -i "rtsp://user:pass@ip:554/stream1"

# Riaggiunge telecamera con script aggiornato
./add_camera.sh
```

#### "Ambiente virtuale non trovato"
```bash
./install.sh
```

#### "Credenziali non cifrate"
```bash
source venv/bin/activate
python3 -c "from security_manager import SecurityManager; SecurityManager('config.ini').encrypt_existing_credentials()"
```

#### "Errore mount disco esterno"
```bash
# Verifica dispositivo
lsblk | grep -E "sd[b-z]"

# Verifica mount point
df -h | grep -E "/media|/mnt"

# Riconfigura storage
source venv/bin/activate
python3 configure.py
```

#### "Telecamera non si connette"
```bash
# Test connessione diretta
ffprobe -timeout 10000000 -i "rtsp://user:pass@ip:554/stream1" -t 5

# Verifica configurazione telecamera
source venv/bin/activate
python3 add_camera.py list

# Riconfigura telecamera
./add_camera.sh
```

#### "Errori lingua/localizzazione"
```bash
# Verifica file traduzioni
ls -la lang/

# Verifica configurazione lingua
grep -A2 "\[LANGUAGE\]" config.ini

# Ripara file lingua mancanti
./install.sh  # Reinstalla i file lingua
```

### **Log e Diagnostica**

#### **Log principali**
```bash
# Log NVR principale
tail -f logs/nvr.log

# Log bot Telegram
tail -f logs/telegram_bot.log

# Log specifico telecamera
tail -f logs/ffmpeg_NomeTelecamera.log

# Log systemd servizi
sudo journalctl -u nvr -f
sudo journalctl -u telegram_bot -f
```

#### **Test componenti**
```bash
# Test ambiente virtuale
source venv/bin/activate
python3 -c "import cryptography, psutil, requests; print('✅ Dipendenze OK')"

# Test configurazione
python3 -c "from config import *; print('✅ Configurazione OK')"

# Test telecamere configurate
python3 -c "from config import load_camera_config; print(f'✅ {len(load_camera_config(\"config.ini\"))} telecamere configurate')"

# Test traduzioni
python3 -c "from language_manager import init_language, get_translation; init_language(); print('✅ Sistema multilingua OK')"

# Test cifratura
python3 -c "from security_manager import SecurityManager; sm = SecurityManager('config.ini'); print('✅ Sistema cifratura OK')"
```

#### **Diagnostica Telegram**
```bash
# Test connessione bot
source venv/bin/activate
python3 -c "
from telegram_bot import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import requests
response = requests.get(f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe')
print('✅ Bot OK' if response.status_code == 200 else '❌ Bot ERROR')
"

# Invia messaggio di test
python3 -c "
from telegram_notifier import send_telegram_message
send_telegram_message('🧪 Test messaggio dal sistema NVR')
"
```

## 🧪 Test di Funzionamento

### **Test Installazione Completa**
```bash
# Test ambiente virtuale e dipendenze
source venv/bin/activate
python3 -c "
import cryptography, psutil, requests, telebot
print('✅ Tutte le dipendenze installate correttamente')
"

# Test configurazione sistema
python3 -c "
from config import CONFIG_FILE, REGISTRAZIONI_DIR
from language_manager import init_language
from security_manager import SecurityManager
print('✅ Configurazione sistema caricata')
print(f'📁 Directory registrazioni: {REGISTRAZIONI_DIR}')
"

# Test servizi systemd
systemctl is-active nvr telegram_bot
echo "✅ Servizi systemd attivi"

# Test telecamere configurate
python3 -c "
from config import load_camera_config
cameras = load_camera_config('config.ini')
print(f'✅ {len(cameras)} telecamere configurate: {list(cameras.keys())}')
"
```

### **Test Funzionalità Avanzate**
```bash
# Test bot Telegram
python3 -c "
from telegram_notifier import send_telegram_message
send_telegram_message('🧪 Test sistema NVR - Installazione completata!')
print('✅ Messaggio di test inviato via Telegram')
"

# Test cifratura/decifratura
python3 -c "
from security_manager import SecurityManager
sm = SecurityManager('config.ini')
test_encrypted = sm.encrypt_password('test123')
test_decrypted = sm.decrypt_password(test_encrypted)
assert test_decrypted == 'test123'
print('✅ Sistema cifratura funzionante')
"

# Test multilingua
python3 -c "
from language_manager import init_language, get_translation
init_language()
print('✅ Sistema multilingua attivo')
print(f'🌐 Lingua: {get_translation(\"install\", \"title\")}')
"
```

### **Test Connessione Telecamere**
```bash
# Test automatico tutte le telecamere
source venv/bin/activate
python3 -c "
from config import load_camera_config
from add_camera import test_camera_connection
cameras = load_camera_config('config.ini')
for name, config in cameras.items():
    print(f'🔍 Test {name}...', end=' ')
    success = test_camera_connection(
        config['ip'], config['port'], 
        config['username'], config['password'], 
        config['path']
    )
    print('✅ OK' if success else '❌ ERRORE')
"
```

## 🔒 Sicurezza

### **File sensibili protetti**
- `config.ini` - Contiene credenziali cifrate (permessi 600)
- `.nvr_key` - Chiave di cifratura AES-256-CBC (permessi 600)
- `logs/` - Log di sistema (permessi 750)

### **Cifratura implementata**
- **AES-256-CBC** per password telecamere e token Telegram
- **Chiave univoca** generata automaticamente per ogni installazione
- **Salt casuale** per ogni cifratura
- **Validazione input** rigorosa per prevenire injection
- **Comandi sistema sicuri** tramite SecureCommandExecutor

### **Backup raccomandati**
```bash
# Backup configurazione completa
cp config.ini config.ini.backup.$(date +%Y%m%d_%H%M%S)
cp .nvr_key .nvr_key.backup.$(date +%Y%m%d_%H%M%S)

# Backup automatico con script
#!/bin/bash
BACKUP_DIR="/percorso/backup/nvr"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
tar czf "$BACKUP_DIR/nvr_backup_$DATE.tar.gz" \
    config.ini .nvr_key lang/ logs/ --exclude="logs/*.log"
```

### **Hardening aggiuntivo raccomandato**
```bash
# Restrizioni permessi
chmod 600 config.ini .nvr_key
chmod 750 logs/
chown root:nvr-group config.ini .nvr_key  # Se usi gruppo dedicato

# Firewall (esempio UFW)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 554/tcp     # RTSP telecamere (solo da LAN)
sudo ufw enable

# Fail2ban per SSH (opzionale)
sudo apt install fail2ban
```

## 🔄 Aggiornamenti

### **Aggiornamento del sistema**
```bash
# 1. Backup configurazione corrente
cp config.ini config.ini.backup.$(date +%Y%m%d_%H%M%S)
cp .nvr_key .nvr_key.backup.$(date +%Y%m%d_%H%M%S)

# 2. Ferma servizi
sudo systemctl stop nvr telegram_bot

# 3. Aggiorna codice da GitHub
git pull origin main

# 4. Aggiorna dipendenze
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 5. Verifica configurazione (se necessario)
python3 configure.py

# 6. Riavvia servizi
sudo systemctl start nvr telegram_bot
sudo systemctl status nvr telegram_bot
```

### **Migrazioni specifiche**

#### **Da versione senza cifratura**
```bash
# Migra credenziali esistenti
source venv/bin/activate
python3 -c "
from security_manager import SecurityManager
sm = SecurityManager('config.ini')
sm.encrypt_existing_credentials()
print('✅ Credenziali migrate e cifrate')
"
```

#### **Da versione senza multilingua**
```bash
# Il sistema è retrocompatibile
# I file lingua vengono creati automaticamente al primo avvio
./install.sh  # Reinstalla solo i file mancanti
```

### **Verifica post-aggiornamento**
```bash
# Test sistema completo
source venv/bin/activate
python3 -c "
print('🧪 Test post-aggiornamento...')
from config import CONFIG_FILE
from language_manager import init_language
from security_manager import SecurityManager
from telegram_notifier import send_telegram_message

# Test componenti
init_language()
sm = SecurityManager(CONFIG_FILE)
send_telegram_message('✅ Sistema NVR aggiornato con successo!')
print('✅ Aggiornamento completato')
"
```

## 🤝 Contributi

### **Come contribuire**
1. **Fork** il repository su GitHub
2. **Crea un branch** per la tua feature: `git checkout -b feature/nuova-funzionalita`
3. **Mantieni la compatibilità** con la configurazione esistente
4. **Aggiungi test** per nuove funzionalità
5. **Aggiorna documentazione** (README, commenti, traduzioni)
6. **Rispetta le linee guida di sicurezza**
7. **Submit una Pull Request**

### **Linee guida sviluppo**
- **Sicurezza first**: validare sempre input utente
- **Multilingua**: aggiornare `lang/it.json` e `lang/en.json`
- **Logging**: usare `multilingual_logging.py` per log localizzati
- **Compatibilità**: mantenere retrocompatibilità configurazione
- **Testing**: testare su installazione pulita

### **Aree di miglioramento**
- 🌐 **Traduzioni** in altre lingue
- � **Interfaccia web** di gestione
- 🔌 **Plugin system** per estensioni
- 📊 **Dashboard** statistiche avanzate
- 🤖 **AI detection** oggetti/persone
- 📡 **Streaming remoto** ottimizzato

## 📄 Licenza

Questo progetto è distribuito sotto **Licenza MIT**.

```
MIT License

Copyright (c) 2025 PWS NVR System

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Vedi file `LICENSE` per il testo completo.

## 🆘 Supporto

### **Dove trovare aiuto**
- 📚 **Documentazione**: Leggi attentamente questo README
- 🔍 **Log di sistema**: Controlla `logs/` per errori specifici
- 🧪 **Test diagnostici**: Usa gli script di test inclusi
- 💬 **Issues GitHub**: [github.com/fapws/pws-nvr/issues](https://github.com/fapws/pws-nvr/issues)

### **Prima di segnalare un problema**
1. **Controlla i log**: `tail -f logs/nvr.log`
2. **Verifica configurazione**: `python3 configure.py`
3. **Testa componenti**: Usa gli script di test del README
4. **Controlla Issues esistenti** su GitHub

### **Informazioni utili per segnalazioni**
- Versione sistema operativo
- Versione Python (`python3 --version`)
- Versione ffmpeg (`ffmpeg -version`)
- Log errori specifici
- Configurazione anonimizzata (rimuovi credenziali)

### **Community e Supporto**
- 🌟 **Star il repository** se ti è utile
- 🔀 **Fork** per contribuire
- � **Issues** per bug e richieste feature
- 💡 **Discussions** per domande generali

---

## 🚀 Quick Start per Utenti Esperti

```bash
# Clone e setup rapido
git clone https://github.com/fapws/pws-nvr.git && cd pws-nvr
chmod +x install.sh && ./install.sh

# Aggiungi telecamere post-installazione
./add_camera.sh

# Controlla stato
sudo systemctl status nvr telegram_bot

# Monitoring
tail -f logs/nvr.log
```

## 📈 Statistiche Sistema

### **Requisiti minimi**
- **OS**: Ubuntu 20.04+ / Debian 11+ / Fedora 35+
- **RAM**: 2GB (4GB raccomandati)
- **Storage**: 10GB sistema + spazio registrazioni
- **CPU**: ARM64/x86_64 con 2+ core
- **Rete**: Connessione stabile per telecamere e Telegram

### **Servizi opzionali (configurazione separata)**
- **Tailscale**: Per accesso remoto VPN sicuro
- **MediaMTX**: Per streaming RTSP ottimizzato
- **Entrambi**: Non installati automaticamente, vedi [Configurazione Servizi Opzionali](#-configurazione-servizi-opzionali)

### **Performance tipiche**
- **Telecamere simultanee**: 4-8 (dipende da hardware)
- **Segmentazione**: File 5 minuti, ~50-200MB per telecamera/ora
- **Latenza Telegram**: <2 secondi per comandi
- **Riavvio automatico**: <30 secondi per processo ffmpeg
- **Storage auto-cleanup**: Quando uso >94.5%

---

**Sistema NVR Universale** - Sicuro, Scalabile, Multilingua 🎥
