# Materia v0.14 — comptes et droits de classe

Cette version remplace l’identité limitée au navigateur par des comptes locaux utilisables pour un pilote en classe.

## Fonctions ajoutées

- page **Mon compte** avec inscription, connexion et déconnexion ;
- profils étudiant, enseignant et administrateur ;
- mots de passe salés et dérivés avec scrypt ;
- rattachement automatique des projets invités au compte lors de la connexion ;
- création de cours réservée aux enseignants et administrateurs ;
- espace classe inaccessible sans compte ;
- validation scientifique réservée à un enseignant ou administrateur possédant aussi le code de revue ;
- migration du schéma SQLite en version 3 et endpoint de santé en version 0.14.0.

## Configuration du pilote

Au premier lancement, Materia génère deux codes locaux distincts dans `data/.teacher_token` et `data/.review_token`. `MATERIA_TEACHER_TOKEN` et `MATERIA_REVIEW_TOKEN` permettent à l’établissement de les remplacer. Les secrets doivent être transmis seulement aux personnes concernées.

## Validation

- 58 tests automatisés réussis ;
- routes principales, santé et disponibilité contrôlées après redémarrage ;
- pages **Mon compte** et **Espace classe** vérifiées dans le navigateur ;
- serveur toujours limité à `127.0.0.1` par défaut.

## Limite restante

Les comptes sont locaux au serveur Materia. Pour un déploiement institutionnel, il reste à connecter le SSO de l’école, le cycle de réinitialisation de mot de passe, une console d’administration et la journalisation de sécurité.
