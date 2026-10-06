# Materia v0.17 — parcours utilisables et données compréhensibles

## Temps et exports

- horizon saisissable en jours, mois ou années dans les estimateurs, les mesures publiées, les comparaisons et l'exercice guidé ;
- conversion documentée avec 365,25 jours par année et 30,4375 jours par mois moyen ;
- axe du graphique, tableaux et CSV exprimés dans l'unité choisie ;
- export CSV disponible pour les projections, observations, mesures publiées et comparaisons.

## Catalogue et matériaux personnalisés

- recherche étendue au nom, famille, classe, sous-type, mécanismes, propriété et notes ;
- filtres par classe, sous-catégorie, mécanisme et niveau de données ;
- tri par nom, famille, maturité ou quantité de données ;
- bouton de réinitialisation ;
- création d'une fiche personnalisée avec nom, abréviation, famille, module initial, mécanismes et référence ;
- utilisation immédiate de la fiche dans l'estimateur et la comparaison, avec statut utilisateur non validé.

## Comparaison

- comparaison de un à quatre matériaux réels ou personnalisés sous des conditions communes ;
- exercice A/B/C corrigé : les polymères fictifs peuvent être sélectionnés ensemble ;
- comparaison des projets enregistrés maintenue ;
- export CSV long pour reprendre les courbes dans Python, Excel ou un tableur.

## Origine du module PP

La valeur de 604,1 MPa est affichée comme **module initial moyen publié** du système R-PP1x. Elle correspond à sept éprouvettes du grade PP H301 de Braskem, après un cycle d'extrusion puis injection, testées selon ASTM D638 à 50 mm/min et à température ambiante. Elle ne représente pas une valeur générique de tous les PP.

Référence : Matos et al., *Polymers* 2024, 16, 1788, tableau 2, DOI `10.3390/polym16131788`.

## Validation

- 61 tests automatisés réussis ;
- comparaison PP/LDPE et exercice Polymère A/B contrôlés dans l'interface ;
- formulaire de matériau personnalisé et nouveaux filtres contrôlés ;
- provenance PP, DOI, protocole et export CSV vérifiés.
