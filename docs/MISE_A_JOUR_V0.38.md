# Materia v0.38 — distribution GitHub multiplateforme

Cette version rend le projet distribuable sur macOS, Windows et Linux.

- lanceur Python commun avec création automatique de l'environnement ;
- lanceurs en double-clic pour macOS et Windows ;
- exclusion conditionnelle de `uvloop` sous Windows ;
- hôte et port configurables ;
- image Docker non-root avec contrôle de santé et volume persistant ;
- tests GitHub Actions sur Python 3.11 et 3.13 sous les trois systèmes ;
- publication d'images `amd64` et `arm64` dans GitHub Container Registry ;
- protection Git contre l'ajout de comptes, sessions, PDF, sauvegardes et secrets ;
- documentation d'installation, contribution, sécurité et rapport de bug.

Une application NiceGUI ne peut pas être publiée avec GitHub Pages. L'accès public utilise l'image Docker derrière HTTPS et un volume `/app/data` persistant.
