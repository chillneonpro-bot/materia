# Étude de validation du modèle PP H301 — Materia v0.40

## Objectif

Cette étude cherche à obtenir une courbe plus exploitable sans demander de nouvelle expérience à l'utilisateur. Elle vérifie le modèle sur un cas réel homogène avant de réduire la largeur affichée.

Le cas retenu est le polypropylène H301 retransformé étudié par Matos et al. dans *Natural Aging of Reprocessed Polypropylene Composites Filled with Sustainable Corn Fibers*, DOI `10.3390/polym16131788`. Le tableau 2 fournit quatre formulations, trois temps de vieillissement naturel, sept éprouvettes par point, la moyenne du module de Young et son écart-type.

## Données publiées

| Formulation | E0 (MPa) | E30 (MPa) | E120 (MPa) |
|---|---:|---:|---:|
| R-PP1x | 604,1 ± 9,0 | 561,8 ± 40,3 | 555,8 ± 20,5 |
| R-PP3x | 516,9 ± 10,9 | 465,2 ± 21,4 | 454,9 ± 30,2 |
| R-PP3x/3CHF | 537,1 ± 9,9 | 504,9 ± 20,1 | 488,8 ± 15,8 |
| R-PP3x/5CHF | 541,1 ± 8,4 | 492,4 ± 30,9 | 481,6 ± 40,1 |

## Protocole de comparaison aveugle

Pour chacune des quatre formulations :

1. la formulation cible est entièrement retirée du calibrage ;
2. seul son module initial E0 est conservé, comme il le serait depuis une fiche matériau ;
3. Materia calcule la rétention médiane à 30 et 120 jours à partir des trois autres formulations ;
4. cette rétention est multipliée par E0 ;
5. les valeurs prédites sont comparées aux valeurs masquées du tableau 2.

Le modèle réalise ainsi huit prédictions qu'il n'a pas utilisées pour construire la courbe cible.

## Résultats comparatifs

| Formulation masquée | Temps (jours) | Mesuré (MPa) | Prédit (MPa) | Écart (MPa) | Erreur relative |
|---|---:|---:|---:|---:|---:|
| R-PP1x | 30 | 561,8 | 549,7 | −12,1 | 2,15 % |
| R-PP1x | 120 | 555,8 | 537,7 | −18,1 | 3,26 % |
| R-PP3x | 30 | 465,2 | 480,7 | +15,5 | 3,33 % |
| R-PP3x | 120 | 454,9 | 470,4 | +15,5 | 3,41 % |
| R-PP3x/3CHF | 30 | 504,9 | 488,8 | −16,1 | 3,20 % |
| R-PP3x/3CHF | 120 | 488,8 | 478,0 | −10,8 | 2,20 % |
| R-PP3x/5CHF | 30 | 492,4 | 503,2 | +10,8 | 2,20 % |
| R-PP3x/5CHF | 120 | 481,6 | 492,4 | +10,8 | 2,25 % |

### Indicateurs globaux

- erreur absolue moyenne : **13,72 MPa** ;
- RMSE : **13,99 MPa** ;
- erreur relative moyenne : **2,75 %** ;
- erreur relative moyenne à 30 jours : **2,72 %** ;
- erreur relative moyenne à 120 jours : **2,78 %** ;
- erreur relative maximale : **3,41 %** ;
- R² sur les huit valeurs masquées : **0,854**.

## Construction de la nouvelle bande

Dans la fenêtre observée de 0 à 120 jours, la demi-largeur retenue est l'erreur relative maximale des huit prédictions masquées, soit **±3,41 %** autour de la courbe centrale. Les huit valeurs masquées sont contenues dans cette bande, soit une couverture empirique interne de **100 %**.

Cette bande vise une lecture à 80 %, mais l'échantillon est trop petit pour revendiquer une garantie externe. Le mot « interne » reste donc affiché dans le logiciel.

Après 120 jours, Materia ne conserve pas artificiellement ±3,41 %. La borne basse prolonge la vitesse tardive la plus rapide observée parmi les quatre formulations et la borne haute la vitesse la plus lente. La largeur augmente ainsi avec l'extrapolation.

## Effet sur un scénario comparable

Exemple : PP, E0 = 1 100 MPa, exposition extérieure, horizon de deux ans, seuil à 80 %.

| Résultat | Modèle v0.39 | Modèle v0.40 |
|---|---:|---:|
| Module central à 120 jours | 990,1 MPa | 990,1 MPa |
| Bornes à 120 jours | 520,4–1 502,2 MPa | 956,3–1 023,8 MPa |
| Largeur relative à 120 jours | 99,2 % | 6,8 % |
| Module central à deux ans | 533,1 MPa | 851,2 MPa |
| Bornes à deux ans | 371,1–686,9 MPa | 767,6–951,9 MPa |
| Largeur relative à deux ans | 59,2 % | 21,7 % |
| Franchissement central de 80 % | environ 8 mois | environ 1 an et 8 mois |

La modification ne consiste pas seulement à réduire graphiquement la zone : elle retire du calcul principal des campagnes portant sur d'autres grades et d'autres climats. Ces publications restent dans la base comme preuves contextuelles et contrôles de transférabilité.

## Interprétation permise

Entre 0 et 120 jours, la nouvelle courbe est la meilleure estimation interne disponible pour le cas PP H301 et les formulations proches de l'étude. La bande ±3,41 % décrit l'erreur du modèle sur les formulations masquées, pas la dispersion complète des éprouvettes.

Au-delà de 120 jours, la courbe devient une extrapolation. À deux ans, la plage 767,6–951,9 MPa est fondée sur les vitesses tardives extrêmes observées, mais aucune mesure à deux ans n'est disponible dans la publication.

Le modèle ne doit pas être transféré sans réserve à un PP stabilisé UV, un autre grade, une autre épaisseur, un autre climat ou un produit fortement chargé. Le logiciel conserve ces limites dans le rapport et les exports.

## Conclusion

Le cas PP H301 est désormais contrôlé directement contre huit valeurs laissées hors calibrage. L'erreur relative moyenne de 2,75 % justifie une bande interne nettement plus serrée jusqu'à 120 jours. L'élargissement après 120 jours dépend des vitesses réellement observées, ce qui remplace l'ancienne sensibilité générique par une règle traçable et reproductible.
