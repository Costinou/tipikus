#!/usr/bin/env bash

set -e

PYTHON_VERSION="3.13"
PYTHON_BIN="python${PYTHON_VERSION}"
VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"
APP_FILE="app.py"

LOG_DIR="/var/log/tipikus"
LOG_FILE="${LOG_DIR}/tipikus.log"

echo "=== Setup de l'application Python ==="

# 0. Créer le dossier de logs si nécessaire
if [ ! -d "$LOG_DIR" ]; then
    echo "[+] Création du dossier de logs : $LOG_DIR"
    sudo mkdir -p "$LOG_DIR"
    sudo chown "$USER":"$USER" "$LOG_DIR"
else
    echo "[✓] Dossier de logs existant"
fi

# 1. Installer Python 3.13 si absent
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo "[+] Python $PYTHON_VERSION non trouvé, installation..."

    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install -y python3.13 python3.13-venv python3.13-dev
else
    echo "[✓] Python $PYTHON_VERSION déjà installé"
fi

# 2. Installer pip si absent
if ! $PYTHON_BIN -m pip --version &> /dev/null; then
    echo "[+] pip non trouvé, installation..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | $PYTHON_BIN
else
    echo "[✓] pip déjà installé"
fi

# 3. Créer le venv si absent
if [ ! -d "$VENV_DIR" ]; then
    echo "[+] Création du virtualenv"
    $PYTHON_BIN -m venv $VENV_DIR
else
    echo "[✓] Virtualenv déjà existant"
fi

# 4. Activer le venv
echo "[+] Activation du virtualenv"
source $VENV_DIR/bin/activate

# 5. Installer les dépendances
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "[+] Installation / mise à jour des dépendances"
    pip install --upgrade pip
    pip install -r $REQUIREMENTS_FILE
else
    echo "[!] requirements.txt introuvable, étape ignorée"
fi

# 6. Lancer l'application en arrière-plan (stdout + stderr ensemble)
echo "[+] Lancement de l'application en nohup"
nohup python3 $APP_FILE \
    </dev/null \
    >> "$LOG_FILE" 2>&1 &

echo "=== Application lancée ==="
echo "PID: $!"
echo "Logs: $LOG_FILE"