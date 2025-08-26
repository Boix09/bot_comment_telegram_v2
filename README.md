# bot_comment_telegram_v2

Projet : bot Telegram (Telethon) — rapide et fiable — prêt pour Termux.

**Contenu**
- `main.py` : point d'entrée
- `bot.py` : logique principale (événements, envoi rapide, fallback, poller, keep-alive)
- `config.example.py` : fichier d'exemple à copier en `config.py` et remplir
- `logger.py` : configuration de logs (console + rotation fichier)
- `requirements.txt` : dépendances
- `.gitignore` : pour éviter de commiter secrets / sessions

## Avant de lancer (Termux)
1. Copier le dossier sur Termux (ou cloner depuis GitHub).
2. Installer les paquets :
   ```bash
   pkg update -y && pkg upgrade -y
   pkg install git python -y
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Copier `config.example.py` en `config.py` et remplir tes valeurs :
   ```bash
   cp config.example.py config.py
   nano config.py
   ```
4. Lancer le bot :
   ```bash
   python main.py
   ```
   La première exécution te demandera un code Telegram (SMS / Telegram) pour authentifier le compte.

## Fichiers importants
- **config.example.py** : ne mets jamais tes vraies clés dans un repo public. Conserve `config.py` localement.
- **bot.log** : fichier de logs généré par le bot (ajouté à .gitignore).

## Notes
- Ce projet combine l'écoute d'événements Telethon et un *poller* de secours (si l'horloge système pose problème).
- Le bot tente d'envoyer via `comment_to` (chemin le plus court) puis fait un `GetDiscussionMessageRequest` en fallback.
- Respecte les `FloodWaitError` de Telegram — le bot gère automatiquement les pauses.
