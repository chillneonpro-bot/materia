# Materia v0.21 — prédiction aveugle avant essais

## Objectif

La v0.21 prépare la comparaison honnête entre une courbe produite uniquement avec les données documentaires disponibles et des expériences réalisées ultérieurement.

## Gel de la prédiction

Le bouton **Figer avant essais** exporte :

- la courbe centrale et ses bornes ;
- les paramètres et conditions ;
- la source et le niveau de preuve ;
- la date de coupure documentaire ;
- la version du modèle ;
- une empreinte SHA-256 détectant toute modification.

## Comparaison ultérieure

La page `/validation-aveugle` compare le fichier figé à un CSV `time_days,modulus_mpa`. Elle calcule MAE, RMSE, MAPE, biais, couverture de la bande et détail de chaque mesure.

## Données IIR

La publication ouverte Nguyen-Tri et al. 2019, DOI `10.3390/jcs3020048`, est maintenant qualifiée dans la base documentaire. Elle porte sur un composite butyle chargé de noir de carbone, immergé dans le fluide Milform 64 SST entre 80 et 120 °C. Elle n’est pas utilisée pour inventer une courbe à 23 °C dans un liquide non précisé.

## Limite actuelle

Le protocole aveugle est opérationnel. Le corpus multi-études nécessaire pour produire un intervalle prédictif calibré reste à construire famille par famille. Le PP dispose d’un bon contrôle interne à court terme, mais pas encore de validation externe compatible.

## Vérification

- 80 tests automatisés réussis ;
- empreinte invalidée après toute modification du fichier figé ;
- comparaison refusée au-delà de l’horizon gelé ;
- source IIR et domaine de validité enregistrés ;
- route de validation aveugle disponible.
