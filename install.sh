#!/bin/bash
# Sistema di installazione universale per NVR
# Gestisce tutto dall'installazione Python alla configurazione completa

set -e

# Variabili globali
LANGUAGE="en"  # Lingua predefinita: inglese

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzioni di utility
print_header() {
    echo -e "\n${BLUE}===============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===============================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

get_translation() {
    local section=$1
    local key=$2
    shift 2
    
    local file="lang/${LANGUAGE}.json"
    if [ ! -f "$file" ]; then
        # Fallback all'inglese se la lingua selezionata non è disponibile
        file="lang/en.json"
    fi
    
    # Estrai la traduzione dal file JSON
    local translation=$(grep -oP "\"$key\": \"\K[^\"]+" "$file" | head -1)
    
    if [ -z "$translation" ]; then
        # Se non trova la traduzione, restituisci la chiave
        echo "$key"
    else
        # Restituisci la traduzione
        printf "$translation" "$@"
    fi
}

# Funzione per selezionare la lingua
select_language() {
    clear
    echo -e "${BLUE}===============================================${NC}"
    echo -e "${BLUE}       NVR INSTALLATION - LANGUAGE SELECTION       ${NC}"
    echo -e "${BLUE}===============================================${NC}\n"
    
    echo -e "${BLUE}Please select your language / Seleziona la tua lingua:${NC}"
    echo "1) English"
    echo "2) Italiano"
    
    read -p "Choice/Scelta (1-2): " lang_choice
    
    case $lang_choice in
        1|en|EN|english|English)
            LANGUAGE="en"
            print_success "English language selected"
            ;;
        2|it|IT|italiano|Italiano)
            LANGUAGE="it"
            print_success "Lingua italiana selezionata"
            ;;
        *)
            LANGUAGE="en"
            print_warning "Invalid choice. English selected as default / Scelta non valida. Inglese selezionato come predefinito"
            ;;
    esac
    
    echo
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "Non eseguire questo script come root!"
        exit 1
    fi
}

install_python() {
    print_header "$(get_translation "install" "python_installed" "PYTHON3")"
    
    # Verifica se Python3 è installato
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "$(get_translation "install" "python_installed" "$PYTHON_VERSION")"
    else
        print_warning "$(get_translation "install" "python_not_found")"
        
        # Rileva il sistema operativo
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Ubuntu/Debian
            if command -v apt &> /dev/null; then
                sudo apt update
                sudo apt install -y python3 python3-pip python3-venv python3-dev
            # CentOS/RHEL/Fedora
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3 python3-pip python3-venv python3-devel
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y python3 python3-pip python3-venv python3-devel
            else
                print_error "$(get_translation "install" "unsupported_package_manager")"
                exit 1
            fi
        else
            print_error "$(get_translation "install" "unsupported_os" "$OSTYPE")"
            exit 1
        fi
        
        print_success "$(get_translation "install" "python_installed_success")"
    fi
    
    # Verifica pip
    if command -v pip3 &> /dev/null; then
        print_success "pip3 disponibile"
    elif command -v pip &> /dev/null; then
        print_success "pip disponibile"
        # Crea alias per pip3 se non esiste
        if ! command -v pip3 &> /dev/null; then
            alias pip3=pip
        fi
    else
        print_warning "pip non trovato. Installazione in corso..."
        # Prova a installare pip
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command -v apt &> /dev/null; then
                sudo apt update
                sudo apt install -y python3-pip
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3-pip
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y python3-pip
            else
                # Fallback con get-pip.py
                print_warning "Installazione pip tramite get-pip.py..."
                curl -sS https://bootstrap.pypa.io/get-pip.py | python3
            fi
        fi
        
        # Verifica di nuovo
        if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
            print_success "pip installato con successo"
        else
            print_error "Impossibile installare pip. Installa manualmente:"
            print_error "curl -sS https://bootstrap.pypa.io/get-pip.py | python3"
            exit 1
        fi
    fi
}

install_ffmpeg() {
    print_header "INSTALLAZIONE FFMPEG"
    
    # Verifica se ffmpeg è già installato
    if command -v ffmpeg &> /dev/null; then
        FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n 1 | cut -d' ' -f3)
        print_success "ffmpeg già installato: $FFMPEG_VERSION"
    else
        print_warning "ffmpeg non trovato. Installazione in corso..."
        
        # Rileva il sistema operativo
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Ubuntu/Debian
            if command -v apt &> /dev/null; then
                sudo apt update
                sudo apt install -y ffmpeg
            # CentOS/RHEL/Fedora
            elif command -v yum &> /dev/null; then
                # Abilita repository EPEL per ffmpeg
                sudo yum install -y epel-release
                sudo yum install -y ffmpeg ffmpeg-devel
            elif command -v dnf &> /dev/null; then
                # Abilita repository RPM Fusion per ffmpeg
                sudo dnf install -y https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
                sudo dnf install -y ffmpeg ffmpeg-devel
            else
                print_error "Gestore pacchetti non supportato. Installa ffmpeg manualmente."
                exit 1
            fi
        else
            print_error "Sistema operativo non supportato: $OSTYPE"
            exit 1
        fi
        
        # Verifica installazione
        if command -v ffmpeg &> /dev/null; then
            print_success "ffmpeg installato con successo"
        else
            print_error "Impossibile installare ffmpeg automaticamente."
            print_error "Installa manualmente con:"
            print_error "  Ubuntu/Debian: sudo apt install ffmpeg"
            print_error "  CentOS/RHEL: sudo yum install epel-release && sudo yum install ffmpeg"
            print_error "  Fedora: sudo dnf install ffmpeg"
            exit 1
        fi
    fi
}

setup_venv() {
    print_header "CONFIGURAZIONE AMBIENTE VIRTUALE"
    
    if [ -d "venv" ]; then
        print_warning "Ambiente virtuale esistente trovato"
        read -p "Vuoi ricreare l'ambiente virtuale? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf venv
            print_success "Ambiente virtuale rimosso"
        fi
    fi
    
    if [ ! -d "venv" ]; then
        print_warning "Creazione ambiente virtuale..."
        python3 -m venv venv
        print_success "Ambiente virtuale creato"
    fi
    
    # Attiva ambiente virtuale
    source venv/bin/activate
    
    # Aggiorna pip
    print_warning "Aggiornamento pip..."
    python3 -m pip install --upgrade pip
    
    # Installa dipendenze
    print_warning "Installazione dipendenze..."
    python3 -m pip install -r requirements.txt
    
    print_success "Ambiente virtuale configurato"
}

interactive_config() {
    print_header "CONFIGURAZIONE INTERATTIVA"
    
    # Crea file di configurazione temporaneo
    CONFIG_FILE="config.ini"
    
    # Backup se esiste
    if [ -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%s)"
        print_success "Backup configurazione esistente creato"
    fi
    
    # Inizia configurazione
    cat > "$CONFIG_FILE" << EOF
[Logging]
log_dir = logs

[LANGUAGE]
language = $LANGUAGE

EOF
    
    # Configurazione storage
    print_header "CONFIGURAZIONE STORAGE"
    echo "Dove vuoi salvare le registrazioni?"
    echo "1) Disco esterno (richiede mount point e device)"
    echo "2) Cartella locale (nella directory del NVR)"
    echo "3) Percorso personalizzato"
    
    read -p "Scelta (1-3): " storage_choice
    
    if [ "$storage_choice" = "1" ]; then
        read -p "Device del disco esterno (es: /dev/sdb1): " external_device
        read -p "Mount point (es: /media/TOSHIBA): " mount_point
        read -p "Nome cartella registrazioni (default: registrazioni): " rec_folder
        rec_folder=${rec_folder:-registrazioni}
        
        cat >> "$CONFIG_FILE" << EOF
[STORAGE]
rec_folder_name = $rec_folder
storage_size = 450
storage_max_use = 0.945
use_external_drive = true
external_mount_point = $mount_point
external_device = $external_device

EOF
    elif [ "$storage_choice" = "3" ]; then
        read -p "Percorso completo per le registrazioni: " custom_path
        
        cat >> "$CONFIG_FILE" << EOF
[STORAGE]
rec_folder_name = registrazioni
storage_size = 450
storage_max_use = 0.945
use_external_drive = false
custom_path = $custom_path

EOF
    else
        cat >> "$CONFIG_FILE" << EOF
[STORAGE]
rec_folder_name = registrazioni
storage_size = 450
storage_max_use = 0.945
use_external_drive = false

EOF
    fi
    
    # Configurazione Telegram
    print_header "CONFIGURAZIONE TELEGRAM"
    read -p "Token del bot Telegram: " telegram_token
    read -p "Chat ID per le notifiche: " chat_id
    read -p "IP Tailscale (opzionale, premi Enter per saltare): " tailscale_ip
    
    cat >> "$CONFIG_FILE" << EOF
[TELEGRAM]
bot_token = $telegram_token
chat_id = $chat_id
ip = $tailscale_ip

EOF
    
    # Configurazione telecamere
    print_header "CONFIGURAZIONE TELECAMERE"
    configure_manual_cameras
    
    print_success "Configurazione completata"
}

install_systemd_service() {
    print_header "INSTALLAZIONE SERVIZIO SYSTEMD"
    
    read -p "Vuoi installare i servizi systemd per avvio automatico? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return
    fi
    
    CURRENT_DIR=$(pwd)
    CURRENT_USER=$(whoami)
    
    # Servizio NVR principale
    NVR_SERVICE_FILE="/etc/systemd/system/nvr.service"
    sudo tee "$NVR_SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=NVR Recording System
After=network.target telegram-bot.service
Wants=telegram-bot.service

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python3 $CURRENT_DIR/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Servizio Telegram Bot (indipendente)
    TELEGRAM_SERVICE_FILE="/etc/systemd/system/telegram-bot.service"
    sudo tee "$TELEGRAM_SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=NVR Telegram Bot
After=network.target
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python3 $CURRENT_DIR/telegram_bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable nvr.service
    sudo systemctl enable telegram-bot.service
    
    print_success "Servizi systemd installati"
    print_warning "Usa 'sudo systemctl start telegram-bot' per avviare il bot Telegram"
    print_warning "Usa 'sudo systemctl start nvr' per avviare il sistema di registrazione"
    print_warning "Il bot Telegram può controllare l'NVR indipendentemente"
}

test_camera_rtsp() {
    local ip=$1
    local port=$2
    local username=$3
    local password=$4
    local path=$5
    
    print_warning "$(get_translation "install" "test_rtsp" "$ip" "$port")"
    
    # Costruisci URL RTSP
    if [ -n "$username" ] && [ -n "$password" ]; then
        rtsp_url="rtsp://$username:$password@$ip:$port/$path"
    else
        rtsp_url="rtsp://$ip:$port/$path"
    fi
    
    # Test con ffprobe (più leggero di ffmpeg)
    if command -v ffprobe &> /dev/null; then
        if timeout 10 ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$rtsp_url" >/dev/null 2>&1; then
            print_success "$(get_translation "install" "rtsp_success" "$ip" "$port" "$path")"
            return 0
        fi
    fi
    
    print_error "$(get_translation "install" "rtsp_failure" "$ip" "$port" "$path")"
    return 1
}

configure_manual_cameras() {
    camera_count=0
    while true; do
        camera_count=$((camera_count + 1))
        echo -e "\n${BLUE}$(get_translation "install" "manual_camera" "$camera_count")${NC}"
        
        read -p "$(get_translation "install" "camera_name") " camera_name
        if [ -z "$camera_name" ]; then
            break
        fi
        
        read -p "$(get_translation "install" "camera_ip") " camera_ip
        read -p "$(get_translation "install" "camera_port") " camera_port
        camera_port=${camera_port:-554}
        
        read -p "$(get_translation "install" "camera_path") " camera_path
        read -p "$(get_translation "install" "camera_path2") " camera_path2
        
        read -p "$(get_translation "install" "camera_username") " camera_username
        read -s -p "$(get_translation "install" "camera_password") " camera_password
        echo
        
        # Test connessione se RTSP
        if [ "$camera_port" == "554" ]; then
            if test_camera_rtsp "$camera_ip" "$camera_port" "$camera_username" "$camera_password" "$camera_path"; then
                print_success "$(get_translation "install" "test_success")"
            else
                print_warning "$(get_translation "install" "test_failure")"
            fi
        fi
        
        cat >> "$CONFIG_FILE" << EOF
[$camera_name]
ip = $camera_ip
port = $camera_port
path = $camera_path
path2 = $camera_path2
username = $camera_username
password = $camera_password

EOF
        
        read -p "$(get_translation "install" "add_another_camera") (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            break
        fi
    done
}

main() {
    check_root
    
    # Selezione lingua
    select_language
    
    # Carica i messaggi tradotti
    local title=$(get_translation "install" "title")
    local welcome=$(get_translation "install" "welcome")
    local cancel_any_time=$(get_translation "install" "cancel_any_time")
    local continue_install=$(get_translation "install" "continue_install")
    local installation_cancelled=$(get_translation "install" "installation_cancelled")
    
    print_header "$title"
    echo -e "${BLUE}$welcome${NC}"
    echo -e "${BLUE}$cancel_any_time${NC}\n"
    
    read -p "$continue_install (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "$installation_cancelled"
        exit 0
    fi
    
    # Verifica requirements.txt
    if [ ! -f "requirements.txt" ]; then
        print_error "$(get_translation "install" "file_not_found" "requirements.txt")"
        exit 1
    fi
    
    install_python
    install_ffmpeg
    setup_venv
    interactive_config
    
    # Attiva ambiente virtuale per i prossimi passi
    source venv/bin/activate
    
    # Cifra le credenziali
    print_header "CIFRATURA CREDENZIALI"
    python3 -c "
from security_manager import migrate_config_to_encrypted
migrate_config_to_encrypted('config.ini')
print('✅ Credenziali cifrate automaticamente')
"
    
    install_systemd_service
    
    print_header "INSTALLAZIONE COMPLETATA"
    print_success "Sistema NVR installato e configurato con successo!"
    echo -e "\n${GREEN}Comandi disponibili:${NC}"
    echo -e "  ${BLUE}./start_nvr.sh${NC}               - Avvia il sistema NVR manualmente"
    echo -e "  ${BLUE}source activate_venv.sh${NC}      - Attiva ambiente virtuale"
    echo -e "  ${BLUE}sudo systemctl start telegram-bot${NC} - Avvia servizio bot Telegram"
    echo -e "  ${BLUE}sudo systemctl start nvr${NC}     - Avvia servizio di registrazione"
    echo -e "\n${GREEN}Gestione servizi:${NC}"
    echo -e "  ${BLUE}sudo systemctl status telegram-bot${NC} - Stato bot Telegram"
    echo -e "  ${BLUE}sudo systemctl status nvr${NC}          - Stato sistema registrazione"
    echo -e "  ${BLUE}sudo systemctl stop nvr${NC}            - Ferma registrazioni"
    echo -e "  ${BLUE}sudo systemctl restart telegram-bot${NC} - Riavvia bot Telegram"
    echo -e "\n${GREEN}File di configurazione:${NC}"
    echo -e "  ${BLUE}config.ini${NC}              - Configurazione principale"
    echo -e "  ${BLUE}logs/${NC}                   - Directory log"
    echo -e "\n${YELLOW}IMPORTANTE:${NC}"
    echo -e "  - Le credenziali sono ora cifrate nel file config.ini"
    echo -e "  - Il file .nvr_key contiene la chiave di cifratura"
    echo -e "  - Non condividere il file .nvr_key con nessuno"
    echo -e "  - Fai backup regolari della configurazione"
    echo -e "  - Il bot Telegram funziona indipendentemente dall'NVR"
    echo -e "  - Avvia PRIMA il bot Telegram, poi l'NVR se necessario"
}

main "$@"
