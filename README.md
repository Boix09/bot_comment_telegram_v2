# bot\_comment\_telegram\_v2

Bot Telegram (Telethon) — conçu pour être **rapide, fiable** et facile à exécuter sur **Termux**.
Ce dépôt contient une version prête à l'emploi qui commente automatiquement les nouveaux posts d'un channel (avec fallback, retry et logs).

---

## ⚠️ Avertissements importants (lire avant d'utiliser)

* **Ne violez pas** les conditions d'utilisation de Telegram. L'automatisation abusive peut mener à des sanctions (suspension / ban).
* **Ne publie jamais** tes identifiants (`API_ID`, `API_HASH`, `PHONE_NUMBER`) ni ton fichier de session (`*.session`) dans un repo public. Utilise `config.example.py` pour le repo et garde `config.py` local seulement.
* Ce bot est fourni à titre éducatif — tu es responsable de l'usage que tu en fais.

---

## Contenu du repo

* `main.py` — point d'entrée (démarre le bot).
* `bot.py` — logique principale : écoute d'événements, envoi rapide (`comment_to`), fallback vers discussion, poller de secours, keep-alive, gestion des erreurs/FloodWait.
* `config.example.py` — **exemple** de configuration. Copie-le en `config.py` et remplis tes valeurs.
* `logger.py` — configuration des logs (console + fichier rotatif `bot.log`).
* `requirements.txt` — dépendances (ex : `telethon==1.36.0`).
* `.gitignore` — empêche de committer `config.py`, `*.session`, `bot.log`, etc.

---

## Prérequis (Termux)

* Termux installé (F-Droid recommandé).
* Accès au stockage (pour transférer fichiers) : `termux-setup-storage`.
* Connexion Internet.

---

## Installation (commande-par-commande — copier/coller dans Termux)

1. Mise à jour et paquets de base :

```bash
pkg update -y && pkg upgrade -y
pkg install git python unzip nano -y
pip install --upgrade pip
```

2. Récupérer le code (si tu l'as sur GitHub) :

```bash
cd ~
git clone https://github.com/Boix09/bot_comment_telegram_v2.git
cd bot_comment_telegram_v2
```

Sinon, si tu as un ZIP : place-le dans `~/storage/downloads` puis :

```bash
cp ~/storage/downloads/bot_comment_telegram_full.zip ~/
unzip bot_comment_telegram_full.zip -d bot_comment_telegram_v2
cd bot_comment_telegram_v2
```

3. Installer les dépendances Python :

```bash
pip install -r requirements.txt
```

---

## Configuration (important)

1. Crée le fichier de config local :

```bash
cp config.example.py config.py
nano config.py
```

2. Édite `config.py` et remplace les placeholders par tes valeurs :

```python
API_ID = 123456                # depuis https://my.telegram.org
API_HASH = "your_api_hash"
PHONE_NUMBER = "+509XXXXXXXX"  # ton numéro (ou laisse si tu utilises token)
CHANNEL_USERNAME = "@ton_channel"
GROUP_USERNAME = "@ton_group"   # si inconnu, mets "" (vide)
COMMENT_TEXT = "."
SESSION_NAME = "bot_session"
RETRY_INTERVAL = 0.05
POLL_INTERVAL = 0.25
KEEP_ALIVE_INTERVAL = 20
CLOCK_DELTA_THRESHOLD = 10
```

> Sauvegarde (Ctrl+O) puis quitte (Ctrl+X).

**Remarque** : `config.py` est dans `.gitignore` — ne t’inquiète pas, il ne sera pas poussé sur GitHub.

---

## Lancer le bot (mode interactif — utile pour debug)

```bash
python3 main.py
```

* À la première exécution, Telethon te demandera un code envoyé par Telegram (SMS ou app) et éventuellement ton mot de passe 2FA.
* Le fichier de session (`bot_session.session`) sera créé automatiquement.

---

## Lancer en arrière-plan (commande unique + logs)

Tu veux lancer en arrière-plan et voir les logs en direct :

```bash
nohup python3 main.py > logs.txt 2>&1 &
tail -f logs.txt
```

* `nohup ... &` : exécute en arrière-plan.
* `logs.txt` : contient les logs (aussi `bot.log` selon logger).
* `tail -f logs.txt` : affiche les logs en temps réel.

### Arrêter le bot

```bash
pkill -f main.py
```

ou si tu veux tuer un PID spécifique :

```bash
ps aux | grep main.py
kill <PID>
```

---

## Comment modifier le channel / groupe (workflow simple)

1. Ouvre `config.py` :

```bash
nano config.py
```

2. Change `CHANNEL_USERNAME` et/ou `GROUP_USERNAME`. Sauvegarde.
3. Redémarre le bot :

```bash
pkill -f main.py
nohup python3 main.py > logs.txt 2>&1 &
tail -f logs.txt
```

---

## Logs & diagnostic (quelque commandes utiles)

* Voir les derniers logs :

```bash
tail -n 200 logs.txt
```

* Suivre les logs en live :

```bash
tail -f logs.txt
```

* Chercher les erreurs :

```bash
grep -i "error" logs.txt | tail -n 50
grep -i "FloodWait" logs.txt
grep -i "Fast comment" logs.txt
```

### Interprétation rapide des logs

* `✅ Fast comment sent for <id> in XX ms` → message posté rapidement (bon).
* `⏳ Queued (event) for <id>` → le bot a mis en file d'attente (fallback / pas de droits / discussion pas encore créée).
* `System clock is wrong` → problème d'heure (voir ci-dessous).

---

## Dépannage rapide (problèmes fréquents)

### 1) `ModuleNotFoundError: No module named 'config'`

Tu n'as pas créé `config.py`. Fais :

```bash
cp config.example.py config.py
nano config.py
```

### 2) `System clock is wrong` ou horloge décalée

* Vérifie l'heure locale :

```bash
date
```

* Vérifie l'heure distante (optionnel) :

```bash
curl -sS https://worldtimeapi.org/api/ip | jq '.datetime'
```

* Si l'heure Android est incorrecte → Paramètres Android → Activer **Date & heure automatiques**, puis relancer Termux.
* Si tu ne peux pas corriger l'heure, le bot active un **poller de secours** (il lit le dernier message) — c’est déjà implémenté.

### 3) `ChatWriteForbiddenError`

* Ton compte n'a pas le droit d'écrire dans le groupe. Vérifie que ton compte (numéro) est **membre** du groupe ou a les droits.

### 4) `FloodWaitError`

* Telegram impose un délai. Le bot respecte automatiquement le délai et retente plus tard. Mets moins d'instances ou augmente délai pour éviter répétitions.

---

## Tuning et recommandations pour la vitesse (explications)

* `RETRY_INTERVAL` (50 ms par défaut) : délai entre les tentatives dans la file d'attente. 0.05s est un bon compromis performance/stabilité.
* `POLL_INTERVAL` (250 ms par défaut) : si events sont instables, le poller vérifie le dernier message toutes les 250 ms. Baisser augmente CPU/usage réseau.
* `KEEP_ALIVE_INTERVAL` : ping (get\_me) toutes les x secondes pour maintenir la session.
* `COMMENT_TEXT` : garder le message court (ex: `"."`) pour vitesse et probabilité d'acceptation.
* `ConnectionTcpAbridged` est utilisé pour réduire overhead réseau (déjà configuré dans le code).

---

## Bonnes pratiques Git & sécurité

* **Ne jamais** committer `config.py` ni `*.session`. `.gitignore` est déjà configuré pour ça.
* Pour sauvegarder la configuration sans exposer secrets : pousse `config.example.py` avec placeholders.
* Si tu as committé par erreur des secrets → révoque immédiatement les clés (change `API_HASH`/`API_ID` sur my.telegram.org) et supprime le fichier de l'historique (opération avancée : BFG / `git filter-branch`).
* Pour pousser depuis Termux :

```bash
git add .
git commit -m "Modification depuis Termux: <description>"
git push origin main
```

* Si Git demande mot de passe, utilise un **Personal Access Token (PAT)** comme mot de passe (créé sur GitHub → Settings → Developer settings → Personal access tokens).

---

## Notes sur déploiement (optionnel)

* **Render (Background Worker)** : crée un service worker, build via `pip install -r requirements.txt`, start command `python3 main.py`. Définis variables d'environnement pour les secrets (ou utilise `config.py` local mais sur Render il vaut mieux utiliser env vars).
* **Docker** : tu peux dockeriser l’app (image `python:3.11-slim`), copier les fichiers et exécuter `python main.py`. Ajuste healthcheck et restart policy.
* **Multi-instance / scaling** : possible mais attention aux doubles-posts. Utilise Redis pour la coordination (locks) si tu lances plusieurs instances.

---

## FAQ rapide

**Q — Si je modifie `config.py` sur GitHub, est-ce que Termux va récupérer automatiquement ?**
A — Non. GitHub et ta copie locale restent synchrones **seulement** si tu fais `git pull` sur Termux. Les modifications sur GitHub n’apparaissent pas automatiquement sur ton téléphone.

**Q — Dois-je redémarrer le bot après modification ?**
A — Oui. Après changer `config.py` (ou `bot.py`), redémarre le process (kill & relancer / ou relaunch).

**Q — Comment vérifier que le bot a bien commenté ?**
A — Regarde `logs.txt` / `bot.log` : tu verras `Fast comment sent` ou `Queued`. Vérifie aussi le post dans Telegram.

---

## Récapitulatif des commandes essentielles (copier-coller)

```bash
# dans Termux, dossier du projet
cd ~/bot_comment_telegram_v2

# installer deps
pip install -r requirements.txt

# config
cp config.example.py config.py
nano config.py

# lancer (foreground)
python3 main.py

# lancer (background + logs)
nohup python3 main.py > logs.txt 2>&1 &
tail -f logs.txt

# arrêter
pkill -f main.py

# git (push/pull)
git add .
git commit -m "msg"
git push origin main
git pull origin main
```
