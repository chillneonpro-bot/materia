# Sécurité

Ne publiez jamais le contenu de `data/`, `.nicegui/`, `.env`, les bases SQLite, les PDF importés ou les codes enseignant et de revue. Ces chemins sont exclus par `.gitignore` et `.dockerignore`.

Pour signaler une faille, contactez directement le mainteneur du dépôt au lieu de créer une issue publique. N'incluez aucune donnée étudiante réelle dans un rapport de bug.

Une instance accessible sur Internet doit être placée derrière HTTPS, utiliser des secrets uniques dans les variables d'environnement et sauvegarder son volume `data`. SQLite convient à un petit pilote sur un seul serveur ; un déploiement multi-serveur exige une base partagée et une authentification institutionnelle.
