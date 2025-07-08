# 🎥 Sistema NVR Universale

Un sistema di videosorveglianza (NVR) sicuro, modulare e facilmente configurabile per la gestione di telecamere IP con supporto RTSP.

## 🚀 Installazione Rapida

```bash
# Clona o scarica i file nella directory desiderata
cd /percorso/del/tuo/nvr

# Esegui l'installazione automatica
chmod +x install.sh
./install.sh
```

Lo script di installazione gestirà automaticamente:
- ✅ Installazione Python3 e dipendenze
- ✅ Creazione ambiente virtuale
- ✅ Configurazione interattiva telecamere
- ✅ Setup storage (locale/esterno)
- ✅ Configurazione Telegram
- ✅ Cifratura credenziali
- ✅ Installazione servizio systemd (opzionale)

## 📋 Caratteristiche

### 🔒 **Sicurezza**
- **Credenziali cifrate** con AES-256
- **Validazione input** completa
- **Logging sicuro** senza esposizione credenziali
- **Comandi di sistema** validati e sicuri

### 📱 **Controllo Remoto**
- **Bot Telegram** per controllo completo
- **Notifiche automatiche** per eventi critici
- **Monitoraggio temperatura** CPU con shutdown automatico
- **Gestione servizi** (avvio/stop/riavvio)

### 💾 **Gestione Storage**
- **Disco esterno** con mount automatico
- **Cartella locale** per installazioni semplici
- **Percorso personalizzato** per configurazioni avanzate
- **Pulizia automatica** file vecchi quando spazio esaurito

### 🎥 **Registrazione**
- **Segmentazione** video in file da 5 minuti
- **Supporto RTSP** per telecamere IP
- **Resilienza** con riavvio automatico processi
- **Codec copy** per prestazioni ottimali

## 🛠️ Configurazione

### **Prima installazione**
```bash
./install.sh
```

### **Riconfigurazione**
```bash
source venv/bin/activate
python3 configure.py
```

### **Avvio sistema**
```bash
# Avvio manuale
./start_nvr.sh

# Avvio come servizio
sudo systemctl start nvr
sudo systemctl enable nvr  # Avvio automatico
```

## 📁 Struttura Directory

```
nvr/
├── install.sh              # Script installazione automatica
├── configure.py             # Configuratore interattivo
├── start_nvr.sh            # Script avvio sistema
├── main.py                 # Applicazione principale
├── config.ini              # Configurazione (cifrata)
├── requirements.txt        # Dipendenze Python
├── venv/                   # Ambiente virtuale
├── logs/                   # File di log
├── registrazioni/          # Video registrati
└── docs/                   # Documentazione
```

## 🔧 Configurazione Avanzata

### **Variabili d'ambiente**
```bash
# Chiave master personalizzata
export NVR_MASTER_PASSWORD="password_sicura_2025"

# Percorso chiave di cifratura
export NVR_KEY_PATH="/percorso/sicuro/.nvr_key"
```

### **Configurazione Telegram**
1. Crea un bot con [@BotFather](https://t.me/BotFather)
2. Ottieni il token del bot
3. Ottieni il tuo Chat ID da [@userinfobot](https://t.me/userinfobot)
4. Inserisci i dati durante la configurazione

### **Configurazione Storage**

#### **Disco locale**
```ini
[STORAGE]
use_external_drive = false
rec_folder_name = registrazioni
```

#### **Disco esterno**
```ini
[STORAGE]
use_external_drive = true
external_device = /dev/sdb1
external_mount_point = /media/TOSHIBA
rec_folder_name = registrazioni
```

#### **Percorso personalizzato**
```ini
[STORAGE]
use_external_drive = false
custom_path = /percorso/personalizzato/registrazioni
```

## 📱 Comandi Telegram

Una volta configurato il bot, potrai controllare il sistema via Telegram:

- `/nvr_status` - Stato del sistema
- `/nvr_start` - Avvia NVR
- `/nvr_stop` - Ferma NVR
- `/nvr_restart` - Riavvia NVR
- `/reboot` - Riavvia sistema
- `/shutdown` - Spegni sistema
- `/stream` - Link streaming telecamere (con Tailscale)

## 🔍 Monitoraggio

Il sistema monitora automaticamente:
- **Spazio disco** con pulizia automatica
- **Temperatura CPU** con shutdown di sicurezza
- **Stato processi** con riavvio automatico
- **Connessione telecamere** con ripristino automatico

## 🆘 Risoluzione Problemi

### **Errori comuni**

#### "Ambiente virtuale non trovato"
```bash
./install.sh
```

#### "Credenziali non cifrate"
```bash
source venv/bin/activate
python3 migrate_credentials.py
```

#### "Errore mount disco esterno"
```bash
# Verifica device
lsblk

# Verifica mount point
df -h

# Riconfigura storage
python3 configure.py
```

#### "Telecamera non si connette"
```bash
# Testa connessione RTSP
ffmpeg -i "rtsp://user:pass@ip:554/stream1" -t 10 -f null -

# Verifica configurazione
python3 configure.py
```

### **Log di sistema**
```bash
# Log NVR
tail -f logs/nvr.log

# Log specifico telecamera
tail -f logs/ffmpeg_NomeTelecamera.log

# Log sistema
sudo journalctl -u nvr -f
```

## 🧪 Test di Funzionamento

```bash
# Test ambiente
source venv/bin/activate
python3 -c "import cryptography, psutil, requests; print('✅ Dipendenze OK')"

# Test configurazione
python3 -c "from config import *; print('✅ Configurazione OK')"

# Test telecamere
python3 -c "from config import load_camera_config; print(f'✅ {len(load_camera_config(\"config.ini\"))} telecamere configurate')"
```

## 🔒 Sicurezza

### **File sensibili**
- `config.ini` - Contiene credenziali cifrate (permessi 600)
- `.nvr_key` - Chiave di cifratura (permessi 600)
- `logs/` - Log di sistema (permessi 750)

### **Backup raccomandati**
```bash
# Backup configurazione
cp config.ini config.ini.backup.$(date +%Y%m%d)

# Backup chiave cifratura
cp .nvr_key .nvr_key.backup.$(date +%Y%m%d)
```

## 🔄 Aggiornamenti

Per aggiornare il sistema:
```bash
# Backup configurazione
cp config.ini config.ini.backup

# Aggiorna file di sistema
# (mantieni config.ini, .nvr_key e venv/)

# Aggiorna dipendenze
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## 🤝 Contributi

Per contribuire al progetto:
1. Mantieni la compatibilità con la configurazione esistente
2. Aggiungi test per nuove funzionalità
3. Aggiorna la documentazione
4. Rispetta le linee guida di sicurezza

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT. Vedi `LICENSE` per maggiori dettagli.

## 🆘 Supporto

Per supporto e segnalazioni:
- Controlla i log di sistema
- Verifica la configurazione
- Consulta la documentazione completa in `docs/`

## 🔧 Installazione

### 📦 **Installazione Automatica Completa**
```bash
# Scarica e installa tutto automaticamente
./install.sh
```

**Cosa include l'installazione automatica:**
- ✅ **Python3** e pip (se non presenti)
- ✅ **ffmpeg** per registrazione video
- ✅ **nmap** e **curl** per scoperta telecamere
- ✅ **Ambiente virtuale** Python con dipendenze
- ✅ **Scoperta automatica telecamere** sulla rete
- ✅ **Configurazione guidata** interattiva
- ✅ **Cifratura automatica** credenziali
- ✅ **Servizio systemd** (opzionale)

### 📡 **Scoperta Telecamere**

Il sistema include la **scoperta automatica delle telecamere IP** sulla rete locale:

```bash
# Script autonomo per scoperta telecamere
./discover_cameras.sh

# Durante l'installazione
./install.sh  # Include scoperta automatica
```

**Funzionalità scoperta:**
- 🔍 **Scansione automatica** della rete locale
- 📹 **Rilevamento telecamere** su porte comuni (554, 80, 443, 8080, etc.)
- 🏷️ **Riconoscimento marche** (Hikvision, Dahua, Axis, TP-Link, etc.)
- ⚡ **Test connessione RTSP** automatico
- 📋 **Configurazione assistita** con percorsi stream comuni

**Porte scansionate:**
- `554` - RTSP (Real Time Streaming Protocol)
- `80` - HTTP interfaccia web
- `443` - HTTPS interfaccia web
- `8080, 8081, 8000, 8888, 9000` - Porte alternative comuni

**Telecamere supportate:**
- ✅ **Hikvision** - `stream1`, `stream2`
- ✅ **Dahua** - `cam/realmonitor?channel=1&subtype=0`
- ✅ **TP-Link** - `videoMain`, `videoSub`
- ✅ **Axis** - `video.cgi`
- ✅ **Foscam** - `videoMain`
- ✅ **D-Link** - Vari percorsi
- ✅ **Generiche** - `stream`, `video`, `live`

### 🏠 **Installazione Manuale**
