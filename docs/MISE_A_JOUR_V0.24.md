# Materia v0.24 — comparaison prospective aux expériences

## Objectif

La v0.24 transforme la validation aveugle en parcours expérimental utilisable. Une prédiction produite uniquement avec la littérature est figée avant les essais. Les mesures futures sont ensuite comparées à cette version sans réajustement rétroactif.

## Import des mesures futures

- CSV UTF-8 ou Excel `.xlsx`, limité à 5 Mo et 10 000 lignes ;
- colonnes obligatoires `time_days` et `modulus_mpa` ;
- colonne recommandée `replicate_id` pour conserver chaque éprouvette ;
- modèle Excel téléchargeable depuis la page `/validation-aveugle` ;
- rejet des temps négatifs, modules non positifs, valeurs non finies et observations placées après l’horizon gelé.

## Métriques sans surpondération des répétitions

Materia regroupe les répétitions au même temps et calcule leur moyenne, leur écart-type et leur effectif. La MAE, la RMSE, la RMSE normalisée, la MAPE, le biais et la couverture P10–P90 sont calculés sur ces moyennes temporelles. Ainsi, vingt éprouvettes à J0 ne comptent pas comme vingt temps indépendants.

Le premier objectif interne exige au moins cinq temps distincts, une MAPE inférieure ou égale à 10 % et un biais absolu inférieur ou égal à 5 %. Le verdict reste limité à la campagne examinée.

## Restitution

La page affiche la courbe P50 gelée, la bande P10–P90 et les mesures futures avec barres d’écart-type. L’export Excel contient :

- le verdict et les indicateurs ;
- toutes les valeurs de la prédiction et les moyennes expérimentales ;
- un graphique Excel natif ;
- la date de gel, la coupure documentaire, les paramètres et les empreintes SHA-256.

## Intégrité

La vérification du fichier gelé contrôle désormais l’empreinte et la structure numérique complète : longueurs identiques, valeurs finies, temps commençant à zéro et strictement croissant, modules positifs, ainsi que l’ordre borne basse ≤ courbe centrale ≤ borne haute.

## Vérification

La suite automatisée comporte 94 tests couvrant notamment l’import CSV/XLSX, les répétitions, l’intégrité des courbes gelées et le rapport Excel de validation.
