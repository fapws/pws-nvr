#!/bin/bash
# Script di avvio per il sistema NVR con ambiente virtuale
# Eseguire con: ./start_nvr.sh

set -e

echo "🚀 Avvio sistema NVR..."

# Verifica se l'ambiente virtuale esiste
if [ ! -d "venv" ]; then
    echo "❌ Ambiente virtuale non trovato!"
    echo "🔧 Esegui prima: ./setup_environment.sh"
    exit 1
fi

# Attiva l'ambiente virtuale
source venv/bin/activate

# Verifica che le dipendenze siano installate
echo "🔍 Verifica dipendenze..."
python3 -c "import cryptography, psutil, requests; print('✅ Dipendenze verificate')" || {
    echo "❌ Dipendenze mancanti. Installazione in corso..."
    python3 -m pip install -r requirements.txt
}

# Verifica se le credenziali sono cifrate
echo "🔐 Verifica stato credenziali..."
if grep -q "ENC:" config.ini; then
    echo "✅ Credenziali cifrate trovate"
else
    echo "⚠️  Credenziali non cifrate rilevate"
    echo "🔄 Avvio migrazione automatica..."
    python3 -c "
from security_manager import migrate_config_to_encrypted
migrate_config_to_encrypted('config.ini')
print('✅ Credenziali cifrate automaticamente')
"
fi

# Verifica permessi file
echo "🔒 Verifica permessi file..."
chmod 600 config.ini 2>/dev/null || echo "⚠️  Impossibile impostare permessi per config.ini"
chmod 600 .nvr_key 2>/dev/null || echo "ℹ️  File .nvr_key non ancora creato"

# Avvia il sistema NVR
echo "▶️  Avvio sistema NVR..."
python3 main.py
