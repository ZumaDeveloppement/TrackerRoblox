# Tracker Roblox

Outil en ligne de commande pour rechercher le profil public d'un compte Roblox : statut en ligne, amis, groupes, badges, historique de pseudos, jeux crees, tenue d'avatar, et plus.

Cree par **@Zuma**

## Fonctionnalites

- Recherche par pseudo ou par ID Roblox
- Statut en temps reel (hors ligne / en ligne / en jeu / en Studio)
- Profil complet : anciennete du compte, badges, groupes (avec role), amis, followers/following
- Historique des anciens pseudos
- Jeux crees par l'utilisateur
- Tenue d'avatar (items portes)
- Export du profil en `.json` ou `.txt`
- Log optionnel de chaque recherche vers Discord (webhook ou bot)
- Interface terminal en theme sombre (via `rich`)

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

```bash
python tracker.py
```

Tape un pseudo ou un ID Roblox, appuie sur Entree. Tape `quit` pour quitter.

## Configuration (optionnelle)

Copie `config.example.json` en `config.json` pour activer le log Discord :

```bash
cp config.example.json config.json
```

Puis remplis l'un des deux moyens de log (au choix) :

- **Webhook Discord** : `discord_webhook_url`
- **Bot Discord** : `discord_bot_token` + `discord_log_channel_id`

`config.json` est ignore par git — chaque utilisateur garde ses identifiants en local.

## Notes

Utilise uniquement l'API publique Roblox. Aucune donnee privee ou protegee par authentification n'est recuperee.
