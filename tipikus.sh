#!/usr/bin/env bash

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
APP_FILE="$SCRIPT_DIR/app.py"
PID_FILE="$SCRIPT_DIR/tipikus.pid"
LOG_DIR="/var/log/tipikus"
LOG_FILE="${LOG_DIR}/tipikus.log"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher des messages colorés
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérifier que le venv existe
check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_error "Le virtualenv n'existe pas : $VENV_DIR"
        log_info "Exécutez d'abord : python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
}

# Vérifier que app.py existe
check_app() {
    if [ ! -f "$APP_FILE" ]; then
        log_error "Fichier app.py introuvable : $APP_FILE"
        exit 1
    fi
}

# Créer le dossier de logs si nécessaire
setup_logs() {
    if [ ! -d "$LOG_DIR" ]; then
        log_info "Création du dossier de logs : $LOG_DIR"
        sudo mkdir -p "$LOG_DIR"
        sudo chown "$USER":"$USER" "$LOG_DIR"
    fi
}

# Fonction pour démarrer l'application
start() {
    check_venv
    check_app
    setup_logs
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_warn "L'application est déjà en cours d'exécution (PID: $PID)"
            exit 1
        else
            log_warn "Fichier PID obsolète trouvé, suppression..."
            rm -f "$PID_FILE"
        fi
    fi
    
    log_info "Démarrage de Tipikus..."
    
    # Activer le venv et lancer l'application
    source "$VENV_DIR/bin/activate"
    
    nohup python3 "$APP_FILE" >> "$LOG_FILE" 2>&1 &
    
    PID=$!
    echo $PID > "$PID_FILE"
    
    # Attendre un peu pour vérifier que le processus démarre bien
    sleep 2
    
    if ps -p "$PID" > /dev/null 2>&1; then
        log_info "Application démarrée avec succès (PID: $PID)"
        log_info "Logs disponibles dans : $LOG_FILE"
        log_info "Accès : http://localhost:80"
    else
        log_error "Erreur lors du démarrage de l'application"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# Fonction pour arrêter l'application
stop() {
    if [ ! -f "$PID_FILE" ]; then
        log_warn "Aucun fichier PID trouvé, l'application n'est probablement pas en cours d'exécution"
        exit 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ! ps -p "$PID" > /dev/null 2>&1; then
        log_warn "Le processus (PID: $PID) n'existe plus"
        rm -f "$PID_FILE"
        exit 1
    fi
    
    log_info "Arrêt de l'application (PID: $PID)..."
    kill "$PID"
    
    # Attendre que le processus se termine
    TIMEOUT=10
    while ps -p "$PID" > /dev/null 2>&1 && [ $TIMEOUT -gt 0 ]; do
        sleep 1
        TIMEOUT=$((TIMEOUT - 1))
    done
    
    if ps -p "$PID" > /dev/null 2>&1; then
        log_warn "Le processus ne répond pas, arrêt forcé..."
        kill -9 "$PID"
    fi
    
    rm -f "$PID_FILE"
    log_info "Application arrêtée avec succès"
}

# Fonction pour redémarrer l'application
restart() {
    log_info "Redémarrage de l'application..."
    
    if [ -f "$PID_FILE" ]; then
        stop
        sleep 1
    fi
    
    start
}

# Fonction pour afficher le statut
status() {
    if [ ! -f "$PID_FILE" ]; then
        log_warn "L'application n'est pas en cours d'exécution"
        exit 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p "$PID" > /dev/null 2>&1; then
        log_info "L'application est en cours d'exécution (PID: $PID)"
        log_info "URL : http://localhost:5000"
        log_info "Logs : $LOG_FILE"
        
        # Afficher les dernières lignes du log
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Dernières lignes du log :"
            echo "========================"
            tail -n 10 "$LOG_FILE"
        fi
    else
        log_error "Le processus (PID: $PID) n'existe plus"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# Fonction pour afficher les logs en temps réel
logs() {
    if [ ! -f "$LOG_FILE" ]; then
        log_error "Fichier de logs introuvable : $LOG_FILE"
        exit 1
    fi
    
    log_info "Affichage des logs (Ctrl+C pour quitter)..."
    tail -f "$LOG_FILE"
}

# Afficher l'aide
usage() {
    echo "Usage: $0 {start|stop|restart|status|logs}"
    echo ""
    echo "Commandes :"
    echo "  start    - Démarrer l'application"
    echo "  stop     - Arrêter l'application"
    echo "  restart  - Redémarrer l'application"
    echo "  status   - Afficher le statut de l'application"
    echo "  logs     - Afficher les logs en temps réel"
    exit 1
}

# Point d'entrée principal
case "${1:-}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        usage
        ;;
esac