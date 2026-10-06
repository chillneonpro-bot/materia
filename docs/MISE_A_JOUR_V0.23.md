# Materia v0.23 - calibration hors publication

La v0.23 remplace la dispersion calculée entre formulations d’un même article par un premier intervalle prédictif multi-études pour le PP exposé naturellement.

## Données

- 3 publications indépendantes ;
- 6 séries temporelles ;
- 22 valeurs vérifiées ;
- 1 extraction directe de tableau et 2 extractions contrôlées de figures ;
- fenêtre temporelle commune : 0 à 120 jours.

## Calcul

- normalisation de chaque série par son module initial ;
- une voix par publication afin qu’un article contenant plusieurs formulations ne domine pas le modèle ;
- courbe centrale par médiane inter-publications ;
- retrait successif de chaque publication complète ;
- quantiles asymétriques des erreurs logarithmiques hors publication ;
- intervalle pilote P10-P90 qui part du module initial connu et s’élargit progressivement.

La couverture ponctuelle mesurée est de 83,3 % pour une cible de 80 %. Le corpus minimal de trois publications interdit encore une qualification industrielle et explique la largeur de la bande.

## Garde-fous

- une résistance en traction ne peut pas entrer dans un modèle de module de Young ;
- toutes les formulations d’un article restent groupées pendant la validation ;
- les données non vérifiées sont exclues par la requête de base ;
- aucune publication n’est extrapolée pendant le calibrage ;
- les températures moyennes non documentées ne sont pas remplacées par une correction Q10 inventée.

## Validation logicielle

La suite comporte 87 tests, dont un contrôle de non-mélange des propriétés, un contrôle garantissant qu’un article comportant de nombreuses formulations ne compte toujours que comme une source de calibration et une vérification de cohérence entre le manifeste d’extraction et la base.
