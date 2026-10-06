# Materia v0.37 — propriétés initiales recoupées

Cette version enrichit le catalogue sans confondre une fiche technique et une campagne de vieillissement.

## Données ajoutées

- 4 nouveaux matériaux : COC, COP, PPSU et PA11 ;
- 12 profils de module initial pour PP, PC, ABS, PBT, PA66, POM, COC, COP, PPSU et PA11 ;
- 20 nouveaux documents officiels de fabricants ;
- conservation du grade, de la norme, de la température d’essai, du conditionnement, du procédé, de la plage et des deux sources.

Les états sec et conditionné des PA66 et PA11 sont stockés séparément. Les recoupements entre grades ou fabricants sont présentés comme des plages de famille et jamais comme des mesures répétées d’un même grade.

## Comportement du simulateur

Lorsqu’un profil recoupé existe, il remplace la valeur générique de famille comme module initial proposé. La base du calcul indique le grade, la plage officielle, la norme et le conditionnement. Seul le point initial change : en l’absence de série temporelle compatible, la cinétique reste une estimation de famille.

## Interface

La bibliothèque permet de filtrer les matériaux disposant d’un module initial recoupé. Chaque fiche montre la valeur proposée et donne accès aux deux sources officielles ainsi qu’à la note de recoupement.

## Contrôles

Les tests vérifient que chaque profil possède deux sources distinctes, des bornes cohérentes et toutes les conditions d’interprétation. Ils vérifient aussi que les états conditionnés ne remplacent pas silencieusement la valeur à sec proposée par défaut.
