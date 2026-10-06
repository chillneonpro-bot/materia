# Materia v0.13 — classe, rapports et documents

**Date :** 28 septembre 2026

## Classe

- correction d’une remise par l’enseignant ;
- note facultative de 0 à 20 ;
- commentaire pédagogique obligatoire ;
- statut « remis » ou « corrigé » ;
- note et retour visibles dans l’espace étudiant ;
- une nouvelle remise remplace la précédente et remet la correction à zéro ;
- export CSV des notes et export JSON complet ;
- contrôles d’autorisation dans la couche de données.

## Rapports

- export Markdown lisible pour les projections, mesures publiées et exercices ;
- paramètres, modèle, statut, empreinte, niveau de preuve et limites ;
- source et tableau de valeurs principales ;
- mention explicite de l’interdiction d’usage industriel lorsque nécessaire.

## Documents

- les nouveaux PDF ne sont plus encodés dans les enregistrements JSON SQLite ;
- originaux stockés dans `data/documents` avec dossiers et fichiers privés ;
- vérification de l’empreinte SHA-256 avant téléchargement ;
- contrôle du propriétaire avant lecture ;
- migration automatique des anciens PDF Base64 lorsque leur propriétaire ouvre la bibliothèque ;
- suppression coordonnée de la fiche et du fichier original.

## Validation

- sauvegarde ZIP vérifiable de SQLite et des documents ;
- contrôle SHA-256 de chaque fichier et `PRAGMA integrity_check` de la copie ;
- archive locale `data/backups/materia-v0.13.zip` créée puis vérifiée ;
- 52 tests automatisés réussis ;
- compilation Python vérifiée ;
- compatibilité conservée avec les documents et simulations des versions précédentes.
