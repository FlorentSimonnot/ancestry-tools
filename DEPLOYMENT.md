# Guide de Déploiement Automatique

Ce projet est configuré pour un déploiement automatique sur VPS via GitHub Actions avec PM2.

## Configuration GitHub Secrets

Vous devez ajouter les secrets suivants dans votre repository GitHub :
(**Settings** → **Secrets and variables** → **Actions** → **New repository secret**)

| Secret | Description | Exemple |
|--------|-------------|---------|
| `SSH_HOST` | Adresse IP ou domaine de votre VPS | `192.168.1.100` ou `monserveur.com` |
| `SSH_USER` | Nom d'utilisateur SSH | `root` |
| `SSH_PRIVATE_KEY` | Clé privée SSH (déjà configurée) ✅ | Le contenu de votre fichier `~/.ssh/id_rsa` |
| `SSH_PORT` | Port SSH (généralement 22) | `22` |

## Configuration du VPS

### 1. Vérifier que le projet est déjà cloné

Le projet doit déjà être présent dans `/root/ged-papi/ancestry-tools`.

Si ce n'est pas le cas :

```bash
mkdir -p /root/ged-papi
cd /root/ged-papi
git clone https://github.com/VOTRE_USERNAME/VOTRE_REPO.git ancestry-tools
cd ancestry-tools
```

### 2. Installer PM2 (si ce n'est pas déjà fait)

```bash
npm install -g pm2
```

### 3. Configurer PM2 pour démarrer au boot

```bash
pm2 startup
pm2 save
```

### 4. Configurer Git

```bash
cd /root/ged-papi/ancestry-tools
git config --global --add safe.directory $(pwd)
```

### 5. Premier démarrage

```bash
cd /root/ged-papi/ancestry-tools
pm2 start ecosystem.config.js
pm2 save
```

## Déclenchement du Déploiement

Le déploiement se déclenche automatiquement à chaque `git push` sur la branche `main`.

### Déploiement manuel

Si vous voulez déclencher un déploiement manuellement sur le VPS :

```bash
cd /root/ged-papi/ancestry-tools
./deploy.sh
```

## Logs et Debugging

### Voir les logs de l'application avec PM2
```bash
pm2 logs
# ou pour une application spécifique
pm2 logs ancestry-tools
```

### Voir les logs GitHub Actions
Aller dans l'onglet **Actions** de votre repository GitHub.

### Commandes PM2 utiles
```bash
# Statut des applications
pm2 status

# Redémarrer l'application
pm2 restart ecosystem.config.js

# Arrêter l'application
pm2 stop ecosystem.config.js

# Voir les détails d'une application
pm2 show ancestry-tools

# Monitoring en temps réel
pm2 monit
```

### Vérifier que le serveur répond
```bash
curl http://localhost:3001
```

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   GitHub    │         │    GitHub    │         │     VPS     │
│ Repository  │────────▶│   Actions    │────────▶│  (Serveur)  │
│             │  push   │              │   SSH   │             │
└─────────────┘         └──────────────┘         └─────────────┘
                             │
                             │ 1. git pull
                             │ 2. pip install
                             │ 3. pm2 restart
                             ▼
                        ┌─────────────┐
                        │  PM2        │
                        │  ├─ FastAPI │
                        │     :3001   │
                        └─────────────┘
```

## Dépannage

### Le déploiement échoue avec "Permission denied"
- Vérifiez que la clé SSH est correctement configurée
- Vérifiez les permissions du dossier sur le VPS

### L'application ne démarre pas
```bash
pm2 logs
pm2 status
# Vérifier le fichier ecosystem.config.js
```

### Le port 3001 est déjà utilisé
```bash
sudo lsof -i :3001
# Utiliser PM2 pour gérer proprement
pm2 restart ecosystem.config.js
```