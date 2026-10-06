# Déploiement institutionnel de Materia

## Niveau actuellement livré

La version v0.20 est prête pour un pilote mono-serveur supervisé. Elle utilise SQLite en mode WAL, des comptes locaux, des sauvegardes quotidiennes vérifiées et des fichiers conservés sur le serveur.

## Conditions avant ouverture à l'établissement

1. Connecter l'identité de l'école par OIDC ou SAML et désactiver l'inscription locale libre.
2. Migrer les tables vers PostgreSQL avec de vraies migrations versionnées.
3. Stocker les PDF et exports dans un stockage objet sauvegardé.
4. Placer Materia derrière un reverse proxy HTTPS avec en-têtes de sécurité.
5. Centraliser les journaux et les alertes de disponibilité.
6. Définir la durée de conservation des comptes, remises et documents.
7. Faire valider le traitement des données par le DPO de l'établissement.

Le diagnostic machine est disponible sur `/health/readiness`. `pilot_ready` confirme seulement le socle local. `institution_ready` reste faux tant que les dépendances précédentes ne sont pas connectées.

## Tests avant une séance

Lancer Materia, puis exécuter :

```bash
python -m materia.deployment http://127.0.0.1:8087 30
```

La sonde simule trente parcours simultanés en lecture sur la santé du serveur, le catalogue et la page de simulation. Elle ne remplace pas une répétition de séance avec les navigateurs, comptes et fichiers du réseau de l'école.

## Sauvegardes

Au démarrage, Materia crée au plus une archive par jour dans `data/backups/daily` et conserve les quatorze plus récentes. Une exécution manuelle est possible avec :

```bash
python -m materia.maintenance daily
```
