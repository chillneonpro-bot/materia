# Installer et distribuer Materia

## Utilisation locale sur macOS

1. Installer Python 3.11, 3.12 ou 3.13 depuis `python.org`.
2. Télécharger puis décompresser l'archive GitHub de Materia.
3. Double-cliquer sur `Lancer-Materia.command`.
4. Si macOS bloque le premier lancement, effectuer un clic droit sur le fichier, choisir **Ouvrir**, puis confirmer l'ouverture.

Le lanceur crée `.venv`, installe les versions figées et ouvre le navigateur. Il ne modifie pas l'installation Python du système.

## Utilisation locale sur Windows

1. Installer Python 3.11, 3.12 ou 3.13 depuis `python.org`. Le lanceur Python `py` est installé par défaut.
2. Extraire entièrement le ZIP ; ne pas lancer Materia depuis l'aperçu de l'archive.
3. Double-cliquer sur `Lancer-Materia-Windows.bat`.
4. Autoriser Python sur le réseau privé seulement si Windows le demande et si l'accès depuis d'autres postes du réseau est souhaité.

`uvloop` est exclu automatiquement sous Windows. Les chemins de l'environnement virtuel sont choisis selon le système.

## Utilisation manuelle sur Linux

```sh
python3.13 launcher.py
```

Pour un serveur sans navigateur :

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
MATERIA_HOST=0.0.0.0 MATERIA_PORT=8087 .venv/bin/python main.py
```

## Docker

```sh
cp .env.example .env
docker compose up --build -d
```

Le volume `materia-data` conserve la base SQLite, les documents, les secrets et les sauvegardes lors du remplacement du conteneur. Sauvegarder ce volume avant une mise à jour.

Contrôler l'instance :

```sh
curl http://127.0.0.1:8087/health
docker compose logs --tail=100 materia
```

## Publication depuis GitHub

Le workflow `container.yml` construit une image Linux `amd64` et `arm64` dans GitHub Container Registry lorsqu'un tag `v*` est publié. Le workflow `ci.yml` teste chaque modification sous Windows, macOS et Linux et contrôle le démarrage de l'image Docker.

GitHub Pages héberge uniquement des fichiers statiques et ne peut pas faire fonctionner NiceGUI, Python ou SQLite. Pour une URL publique, utiliser l'image Docker sur un serveur ou une plateforme acceptant les conteneurs, monter un volume persistant sur `/app/data`, puis placer l'application derrière un domaine HTTPS.

Dans ce mode, tous les étudiants ouvrent la même adresse dans un navigateur. Ils n'ont rien à installer sur leur Mac ou leur PC ; seul le serveur exécute Python et conserve les comptes, projets et documents.

Variables de serveur :

| Variable | Usage |
|---|---|
| `MATERIA_HOST` | `127.0.0.1` en local, `0.0.0.0` dans Docker |
| `MATERIA_PORT` | Port HTTP, `8087` par défaut |
| `MATERIA_EXTERNAL_URL` | Adresse HTTPS publique utilisée par l'audit de déploiement |
| `MATERIA_TEACHER_TOKEN` | Code enseignant long et unique |
| `MATERIA_REVIEW_TOKEN` | Code indépendant pour la revue scientifique |
| `MATERIA_DB` | Emplacement alternatif de la base SQLite |
| `MATERIA_DOCUMENTS_DIR` | Emplacement alternatif des PDF importés |

## Données exclues de GitHub

La base SQLite, les comptes, les PDF, les sessions, les sauvegardes et les secrets sont ignorés. Seules les données scientifiques explicitement versionnées sous `data/evidence/` appartiennent au dépôt.

Avant chaque publication :

```sh
git status --short
python -m pytest -q
```

Vérifier qu'aucun fichier de `data/`, `.nicegui/`, `.env`, `output/` ou `tmp/` n'apparaît dans la liste.
