#!/bin/bash

# Script de déploiement pour VPS
# Ce script est appelé par GitHub Actions

set -e  # Arrête le script en cas d'erreur

PROJECT_DIR="/root/ged-papi/ancestry-tools"
VENV_DIR="$PROJECT_DIR/venv"

echo "🚀 Début du déploiement..."

# 1. Se positionner dans le répertoire du projet
cd "$PROJECT_DIR"

# 2. Mettre à jour le code
echo "📥 Mise à jour du code depuis Git..."
git pull origin main

# 3. Créer/Activer l'environnement virtuel
echo "🐍 Configuration de l'environnement virtuel..."
if [ ! -d "$VENV_DIR" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# 4. Installer les dépendances
echo "📦 Installation des dépendances..."
pip install -q -r requirements.txt

# 5. Redémarrer l'application avec PM2
echo "🔄 Redémarrage de l'application avec PM2..."
if pm2 describe ged-papi &> /dev/null; then
    # L'application existe déjà dans PM2, on la redémarre
    pm2 restart ged-papi
    echo "✅ Application redémarrée avec PM2"
else
    # L'application n'existe pas, on la démarre
    echo "⚠️  Application non trouvée dans PM2. Démarrage initial..."
    pm2 start /root/ecosystem.config.js
    pm2 save
fi

echo "✅ Déploiement terminé !"
echo "📊 Statut PM2:"
pm2 status