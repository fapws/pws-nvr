#!/bin/bash
# Script per creare un pacchetto distribuibile del sistema NVR

set -e

PACKAGE_NAME="nvr-system"
VERSION="1.0.0"
PACKAGE_DIR="${PACKAGE_NAME}-${VERSION}"

echo "📦 Creazione pacchetto distribuibile NVR..."

# Crea directory temporanea
rm -rf "$PACKAGE_DIR"
mkdir "$PACKAGE_DIR"

# Copia file essenziali (escludi file sensibili e temporanei)
echo "📋 Copiando file essenziali..."

# Lista file da copiare
FILES_TO_COPY=(
    "install.sh"
    "start_nvr.sh" 
    "main.py"
    "config.py"
    "process_manager.py"
    "logging_setup.py"
    "telegram_bot.py"
    "telegram_notifier.py"
    "security_manager.py"
    "secure_executor.py"
    "configure.py"
    "config.ini.example"
    "requirements.txt"
    "README.md"
    "SECURITY_UPDATE.md"
    ".gitignore"
)

# Copia file specificati
for file in "${FILES_TO_COPY[@]}"; do
    if [[ -f "$file" ]]; then
        cp "$file" "$PACKAGE_DIR/"
        echo "  ✅ $file"
    else
        echo "  ⚠️  $file non trovato"
    fi
done

# Crea directory per logs
mkdir -p "$PACKAGE_DIR/logs"

# Crea README per la distribuzione
cat > "$PACKAGE_DIR/INSTALL.md" << 'EOF'
# 🎥 Sistema NVR - Installazione

## 🚀 Installazione Rapida

1. **Estrai il pacchetto:**
   ```bash
   tar -xzf nvr-system-1.0.0.tar.gz
   cd nvr-system-1.0.0
   ```

2. **Esegui l'installazione:**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Avvia il sistema:**
   ```bash
   ./start_nvr.sh
   ```

## 📋 Requisiti

- Linux (Ubuntu/Debian/CentOS/Fedora)
- Python 3.7+
- FFmpeg
- Accesso sudo per installazione dipendenze

## 🔧 Configurazione

Durante l'installazione ti verrà chiesto di configurare:
- Posizione storage registrazioni
- Credenziali telecamere IP
- Token bot Telegram
- Configurazioni opzionali

## 📖 Documentazione

Vedi `README.md` per la documentazione completa.

## 🆘 Supporto

- Controlla i log in `logs/`
- Usa `python3 configure.py` per riconfigurare
- Leggi `SECURITY_UPDATE.md` per dettagli sicurezza
EOF

# Rimuovi file non necessari per la distribuzione
rm -f "$PACKAGE_DIR"/.nvr_key "$PACKAGE_DIR"/config.ini "$PACKAGE_DIR"/create_package.sh

# Crea archivio
tar -czf "${PACKAGE_NAME}-${VERSION}.tar.gz" "$PACKAGE_DIR"

# Pulizia
rm -rf "$PACKAGE_DIR"

echo "✅ Pacchetto creato: ${PACKAGE_NAME}-${VERSION}.tar.gz"
echo ""
echo "📦 Contenuto del pacchetto:"
echo "   - Script di installazione automatica"
echo "   - Sistema NVR completo"
echo "   - Documentazione"
echo "   - Configurazione di esempio"
echo ""
echo "🚀 Per installare:"
echo "   tar -xzf ${PACKAGE_NAME}-${VERSION}.tar.gz"
echo "   cd ${PACKAGE_NAME}-${VERSION}"
echo "   ./install.sh"
