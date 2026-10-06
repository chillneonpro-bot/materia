# Materia v0.19 — validité, campagnes et préparation au déploiement

## Validation du polypropylène

Le centre **Validité** réserve le dernier temps de chaque formulation PP pour un test temporel. Le modèle exponentiel est ajusté sur 0 et 30 jours, puis confronté aux valeurs publiées à 120 jours. Materia affiche MAE, RMSE, erreur relative, R² et le nombre de prédictions situées dans l'écart-type publié.

Ce contrôle reste une validation interne à une publication. Une seconde publication ouverte sur un film PP exposé 90 jours a été qualifiée, puis exclue des métriques : formulation, épaisseur et directions d'essai incompatibles avec le corpus PP H301. Cette exclusion est conservée dans la base avec sa justification.

## Diagnostic de chaque résultat

Chaque parcours peut afficher :

- la nature du résultat : observation, interpolation, extrapolation ou exercice synthétique ;
- la correspondance temporelle, matériau, formulation et environnement ;
- les composantes d'incertitude effectivement quantifiées ;
- les composantes absentes de la bande affichée ;
- l'expérience recommandée pour augmenter le niveau de preuve.

## Gestion des campagnes

- import des mesures en CSV UTF-8 ou Excel `.xlsx` ;
- modèle Excel téléchargeable avec exemples et mode d'emploi ;
- contrôle automatique des temps, valeurs initiales, doublons et variations importantes ;
- séparation entre import utilisateur, revue scientifique et corpus accepté ;
- conservation du matériau, du lot expérimental, des conditions, du protocole, de la source et de l'emplacement dans la source.

## Rapports et classe

Les résultats produisent maintenant un PDF avec courbe vectorielle, paramètres, validité, incertitudes, source et empreinte. Les enseignants disposent d'indicateurs sur les inscrits, remises et corrections, peuvent dupliquer un travail et exporter les notes. Les projets enregistrés peuvent aussi être dupliqués.

## Exploitation

- sauvegarde quotidienne vérifiée au démarrage, avec rétention de 14 archives ;
- sonde non destructive pour 30 parcours simultanés : `python -m materia.deployment http://127.0.0.1:8087 30` ;
- endpoint `/health/readiness` avec diagnostic de déploiement ;
- SQLite, comptes locaux et stockage local restent adaptés au pilote mono-serveur ;
- PostgreSQL, SSO institutionnel, stockage objet, reverse proxy HTTPS et supervision restent requis avant une exploitation institutionnelle multi-serveur.

## Vérification de livraison

- 73 tests automatisés réussis ;
- rapport PDF PP de deux pages rendu et inspecté visuellement ;
- classeur Excel PP relu avec ses quatre feuilles et sa courbe native ;
- les mesures incompatibles de la seconde publication PP restent exclues du score ;
- le pilote de charge à 30 utilisateurs et les routes v0.19 doivent être exécutés après chaque redémarrage du serveur.
