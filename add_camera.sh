#!/bin/bash
# Script per aggiungere telecamere al sistema NVR
# Gestisce automaticamente l'ambiente virtuale

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzioni di utility
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Verifica che siamo nella directory corretta
if [ ! -f "add_camera.py" ]; then
    print_error "Script add_camera.py non trovato nella directory corrente"
    print_info "Assicurati di eseguire questo script dalla directory del NVR"
    exit 1
fi

# Verifica che l'ambiente virtuale esista
if [ ! -d "venv" ]; then
    print_error "Ambiente virtuale non trovato"
    print_info "Esegui prima l'installazione con ./install.sh"
    exit 1
fi

# Verifica che il file di configurazione esista
if [ ! -f "config.ini" ]; then
    print_error "File di configurazione non trovato"
    print_info "Esegui prima l'installazione con ./install.sh"
    exit 1
fi

print_info "Attivazione ambiente virtuale NVR..."

# Attiva l'ambiente virtuale
source venv/bin/activate

# Verifica che l'attivazione sia riuscita
if [ $? -ne 0 ]; then
    print_error "Impossibile attivare l'ambiente virtuale"
    exit 1
fi

print_success "Ambiente virtuale attivato"

# Esegui lo script Python con i parametri passati
print_info "Avvio script gestione telecamere..."
python3 add_camera.py "$@"

# Salva il codice di uscita dello script Python
EXIT_CODE=$?

# Disattiva l'ambiente virtuale
deactivate

if [ $EXIT_CODE -eq 0 ]; then
    print_success "Script completato con successo"
else
    print_warning "Script terminato con codice di uscita: $EXIT_CODE"
fi

exit $EXIT_CODE
