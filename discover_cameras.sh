#!/bin/bash
# Script autonomo per la scoperta delle telecamere IP sulla rete locale

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

check_dependencies() {
    print_header "VERIFICA DIPENDENZE"
    
    missing_deps=()
    
    if ! command -v nmap &> /dev/null; then
        missing_deps+=("nmap")
    fi
    
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Dipendenze mancanti: ${missing_deps[*]}"
        echo "Installa con:"
        echo "  Ubuntu/Debian: sudo apt install ${missing_deps[*]}"
        echo "  CentOS/RHEL: sudo yum install ${missing_deps[*]}"
        echo "  Fedora: sudo dnf install ${missing_deps[*]}"
        exit 1
    fi
    
    print_success "Tutte le dipendenze sono installate"
}

discover_network() {
    print_header "RILEVAMENTO RETE LOCALE"
    
    # Rileva interfacce di rete attive
    interfaces=$(ip route | grep -E '^192\.168\.|^10\.|^172\.' | awk '{print $1}' | sort -u)
    
    if [ -z "$interfaces" ]; then
        print_error "Nessuna rete locale rilevata automaticamente"
        read -p "Inserisci manualmente la rete (es: 192.168.1.0/24): " manual_network
        if [ -z "$manual_network" ]; then
            exit 1
        fi
        echo "$manual_network"
    else
        echo -e "${BLUE}Reti locali rilevate:${NC}"
        
        # Mostra sempre le reti con spiegazione
        local count=1
        while IFS= read -r network; do
            case "$network" in
                192.168.*)
                    echo -e "  ${GREEN}$count. $network${NC} - ${YELLOW}Rete domestica/locale (consigliata)${NC}"
                    ;;
                10.*)
                    echo -e "  ${GREEN}$count. $network${NC} - ${YELLOW}Rete privata aziendale${NC}"
                    ;;
                172.17.*)
                    echo -e "  ${GREEN}$count. $network${NC} - ${YELLOW}Rete Docker (interna)${NC}"
                    ;;
                172.*)
                    echo -e "  ${GREEN}$count. $network${NC} - ${YELLOW}Rete privata${NC}"
                    ;;
                *)
                    echo -e "  ${GREEN}$count. $network${NC} - ${YELLOW}Rete locale${NC}"
                    ;;
            esac
            ((count++))
        done <<< "$interfaces"
        
        # Conta le reti
        network_count=$(echo "$interfaces" | wc -l)
        
        if [ "$network_count" -eq 1 ]; then
            selected_network="$interfaces"
            print_success "Solo una rete disponibile, selezionata automaticamente: $selected_network"
            echo "$selected_network"
        else
            echo
            echo -e "${BLUE}💡 Suggerimento: Scegli la rete 192.168.x.x per trovare telecamere domestiche${NC}"
            while true; do
                read -p "Seleziona il numero della rete da scansionare (1-$network_count): " choice
                
                # Verifica che la scelta sia un numero valido
                if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "$network_count" ]; then
                    selected_network=$(echo "$interfaces" | sed -n "${choice}p")
                    print_success "Rete selezionata: $selected_network"
                    echo "$selected_network"
                    break
                else
                    print_error "Scelta non valida. Inserisci un numero da 1 a $network_count"
                fi
            done
        fi
    fi
}

scan_cameras() {
    local network=$1
    print_header "SCANSIONE TELECAMERE SU $network"
    
    TEMP_FILE=$(mktemp)
    CAMERAS_FOUND=()
    
    echo -e "${BLUE}Scansione in corso... (può richiedere 2-5 minuti)${NC}"
    echo -e "${YELLOW}Porte scansionate: 554 (RTSP), 80 (HTTP), 443 (HTTPS), 8080, 8081, 8000, 8888${NC}\n"
    
    # Scansione rapida con nmap
    echo -e "${BLUE}🔍 Esecuzione scansione nmap...${NC}"
    nmap -sT -p 554,80,443,8080,8081,8000,8888,9000 --open --min-rate 1000 "$network" 2>/dev/null | \
    grep -E "^Nmap scan report|^[0-9]+/tcp open" > "$TEMP_FILE"
    
    # Debug: mostra cosa ha trovato nmap
    echo -e "${BLUE}📋 Dispositivi trovati con porte aperte:${NC}"
    
    # Analizza risultati
    current_ip=""
    current_ports=()
    
    while IFS= read -r line; do
        if [[ $line =~ ^Nmap\ scan\ report\ for\ (.+)\ \(([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\) ]]; then
            # Formato: "Nmap scan report for hostname (IP)"
            hostname="${BASH_REMATCH[1]}"
            current_ip="${BASH_REMATCH[2]}"
            current_ports=()
            echo -e "  ${YELLOW}🔍 $current_ip${NC} ($hostname)"
        elif [[ $line =~ ^Nmap\ scan\ report\ for\ ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+) ]]; then
            # Formato: "Nmap scan report for IP"
            current_ip="${BASH_REMATCH[1]}"
            current_ports=()
            echo -e "  ${YELLOW}🔍 $current_ip${NC}"
        elif [[ $line =~ ^([0-9]+)/tcp\ open ]] && [ -n "$current_ip" ]; then
            port="${BASH_REMATCH[1]}"
            current_ports+=("$port")
            echo -e "    ${GREEN}✅ Porta $port aperta${NC}"
            
            # Processa immediatamente ogni IP quando troviamo l'ultima porta
            # o quando inizia un nuovo IP
        fi
        
        # Quando leggiamo una nuova riga "Nmap scan report" e abbiamo un IP precedente
        if [[ $line =~ ^Nmap\ scan\ report ]] && [ -n "$previous_ip" ] && [ ${#previous_ports[@]} -gt 0 ]; then
            process_device "$previous_ip" "${previous_ports[@]}"
        fi
        
        # Salva IP e porte precedenti
        if [ -n "$current_ip" ]; then
            previous_ip="$current_ip"
            previous_ports=("${current_ports[@]}")
        fi
    done < "$TEMP_FILE"
    
    # Processo ultimo IP se ha porte aperte
    if [ -n "$current_ip" ] && [ ${#current_ports[@]} -gt 0 ]; then
        process_device "$current_ip" "${current_ports[@]}"
    fi
    
    rm -f "$TEMP_FILE"
    echo
    
    # Mostra risultati finali
    show_results
}

process_device() {
    local ip=$1
    shift
    local ports=("$@")
    
    device_info=""
    device_type="Unknown"
    rtsp_port=""
    web_ports=()
    
    # Controlla ogni porta
    for port in "${ports[@]}"; do
        case $port in
            554)
                rtsp_port="554"
                device_type="IP Camera (RTSP)"
                ;;
            80|443|8080|8081|8000|8888|9000)
                web_ports+=("$port")
                # Test interfaccia web
                web_info=$(check_web_interface "$ip" "$port")
                if [ -n "$web_info" ]; then
                    device_type="$web_info"
                fi
                ;;
        esac
    done
    
    # Aggiungi alla lista se sembra una telecamera
    if [ "$device_type" != "Unknown" ] || [ -n "$rtsp_port" ]; then
        CAMERAS_FOUND+=("$ip|$device_type|$rtsp_port|$(IFS=,; echo "${web_ports[*]}")")
        echo -e "${GREEN}📹 $ip${NC} - ${BLUE}$device_type${NC} (porte: ${ports[*]})"
    else
        echo -e "${YELLOW}🔍 $ip${NC} - Dispositivo generico (porte: ${ports[*]})"
    fi
}

check_web_interface() {
    local ip=$1
    local port=$2
    
    for protocol in "http" "https"; do
        # Test connessione con timeout breve
        response=$(timeout 3 curl -s -I "${protocol}://${ip}:${port}/" 2>/dev/null | head -1)
        if [[ $response =~ ^HTTP.*[23][0-9][0-9] ]]; then
            # Controlla contenuto pagina
            content=$(timeout 3 curl -s "${protocol}://${ip}:${port}/" 2>/dev/null | tr '[:upper:]' '[:lower:]' | head -c 2000)
            
            # Riconoscimento marca telecamera
            if [[ $content =~ hikvision ]]; then
                echo "Hikvision Camera"
                return
            elif [[ $content =~ dahua ]]; then
                echo "Dahua Camera"
                return
            elif [[ $content =~ axis ]]; then
                echo "Axis Camera"
                return
            elif [[ $content =~ foscam ]]; then
                echo "Foscam Camera"
                return
            elif [[ $content =~ tp-link ]]; then
                echo "TP-Link Camera"
                return
            elif [[ $content =~ d-link ]]; then
                echo "D-Link Camera"
                return
            elif [[ $content =~ (camera|webcam|ipcam|video|stream) ]]; then
                echo "Generic IP Camera"
                return
            fi
        fi
    done
}

show_results() {
    print_header "RISULTATI SCOPERTA"
    
    if [ ${#CAMERAS_FOUND[@]} -eq 0 ]; then
        print_warning "Nessuna telecamera trovata automaticamente"
        echo -e "${YELLOW}Suggerimenti:${NC}"
        echo "- Verifica che le telecamere siano accese e connesse alla rete"
        echo "- Controlla se usano porte non standard"
        echo "- Alcune telecamere potrebbero avere firewall attivi"
        echo "- Prova a configurare manualmente con gli IP noti"
        return
    fi
    
    print_success "Trovate ${#CAMERAS_FOUND[@]} possibili telecamere:"
    echo
    
    for i in "${!CAMERAS_FOUND[@]}"; do
        IFS='|' read -r ip type rtsp_port web_ports <<< "${CAMERAS_FOUND[i]}"
        
        echo -e "${BLUE}$((i+1)). $ip${NC}"
        echo -e "   Tipo: ${GREEN}$type${NC}"
        if [ -n "$rtsp_port" ]; then
            echo -e "   RTSP: ${GREEN}rtsp://$ip:$rtsp_port/${NC}"
        fi
        if [ -n "$web_ports" ]; then
            echo -e "   Web: ${YELLOW}http://$ip:${web_ports//,/:, http://$ip:}${NC}"
        fi
        echo
    done
    
    # Suggerimenti configurazione
    print_header "SUGGERIMENTI CONFIGURAZIONE"
    echo -e "${BLUE}Percorsi stream comuni:${NC}"
    echo "• Hikvision: stream1, stream2"
    echo "• Dahua: cam/realmonitor?channel=1&subtype=0"
    echo "• TP-Link: videoMain, videoSub"
    echo "• Axis: video.cgi"
    echo "• Foscam: videoMain"
    echo "• Generic: stream, video, live"
    echo
    
    echo -e "${BLUE}Credenziali predefinite comuni:${NC}"
    echo "• admin/admin, admin/password, admin/123456"
    echo "• user/user, guest/guest"
    echo "• root/pass, admin/(vuoto)"
    echo
    
    echo -e "${YELLOW}⚠️ Cambia sempre le credenziali predefinite per sicurezza!${NC}"
}

test_rtsp_connection() {
    print_header "TEST CONNESSIONE RTSP"
    
    read -p "IP telecamera: " test_ip
    read -p "Porta (default 554): " test_port
    test_port=${test_port:-554}
    read -p "Username: " test_user
    read -s -p "Password: " test_pass
    echo
    read -p "Percorso stream (es: stream1): " test_path
    
    # Costruisci URL
    if [ -n "$test_user" ] && [ -n "$test_pass" ]; then
        rtsp_url="rtsp://$test_user:$test_pass@$test_ip:$test_port/$test_path"
        safe_url="rtsp://***:***@$test_ip:$test_port/$test_path"
    else
        rtsp_url="rtsp://$test_ip:$test_port/$test_path"
        safe_url="$rtsp_url"
    fi
    
    echo -e "\n${BLUE}Test connessione: $safe_url${NC}"
    
    if command -v ffprobe &> /dev/null; then
        if timeout 10 ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$rtsp_url" 2>/dev/null; then
            print_success "Connessione RTSP riuscita!"
        else
            print_error "Connessione RTSP fallita"
        fi
    else
        print_warning "ffprobe non disponibile per il test"
    fi
}

main() {
    print_header "SCOPERTA TELECAMERE IP"
    echo -e "${BLUE}Questo script cerca automaticamente telecamere IP sulla rete locale${NC}\n"
    
    check_dependencies
    
    echo "Cosa vuoi fare?"
    echo "1) Scansione automatica rete"
    echo "2) Test connessione RTSP"
    echo "3) Entrambi"
    
    read -p "Scelta (1-3): " choice
    
    case $choice in
        1)
            network=$(discover_network)
            scan_cameras "$network"
            ;;
        2)
            test_rtsp_connection
            ;;
        3)
            network=$(discover_network)
            scan_cameras "$network"
            test_rtsp_connection
            ;;
        *)
            print_error "Scelta non valida"
            exit 1
            ;;
    esac
}

# Esegui solo se script chiamato direttamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
