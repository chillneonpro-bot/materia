# Comparaison de Materia à des essais publiés — v0.46

Date de calcul : 11 octobre 2026.

## But de la comparaison

Cette étude compare une valeur calculée sans voir le point cible à la valeur mesurée dans une publication. Un point ou une campagne est masqué, Materia produit sa prédiction avec les autres données disponibles, puis l’écart est calculé. Ce protocole reproduit l’usage du logiciel sans prétendre à une validation sur un grade industriel indépendant.

Trois systèmes matériaux et trois expositions sont couverts :

- PP H301 et formulations recyclées/composites, vieillissement naturel extérieur jusqu’à 120 jours ;
- composite caoutchouc butyle IIR/BRC, Milform 64 SST à 80, 100 et 120 °C pendant 24 h ;
- composite fibres de lin/époxy, 90 % HR à 20 et 40 °C pendant 38 jours.

## Résultats synthétiques

| Matériau et test masqué | Prédictions | Erreur moyenne MAPE | Erreur maximale | R² | Lecture |
|---|---:|---:|---:|---:|---|
| PP H301, formulation entière masquée | 8 | 2,75 % | 3,41 % | 0,854 | Bon contrôle interne à 30 et 120 jours |
| IIR, temps intérieur masqué | 15 | 8,35 % | 51,38 % | 0,810 | Correct hors transitoire brutal à 120 °C |
| IIR, courbe 100 °C entièrement masquée | 6 | 11,31 % | 28,76 % | -2,154 | Transfert en température rejeté |
| Lin/époxy, campagne de température masquée | 8 | 5,41 % | 11,40 % | 0,975 | Bon contrôle interne dans la fenêtre 0–38 jours |

La plage visuelle commune de Materia correspond à une variation de vitesse de -5 % à +5 %. Elle facilite la comparaison des matériaux mais ne remplace pas les erreurs ci-dessus. Le cas PP reste entièrement dans cette plage. Le lin/époxy la dépasse légèrement à 9 jours. Le transitoire IIR à 120 °C la dépasse fortement et exige les points publiés exacts.

## Cas 1 — PP H301

Pour chaque formulation, Materia cache les valeurs vieillies à 30 et 120 jours. Il conserve seulement son module initial et utilise la rétention des formulations comparables de la même publication.

| Formulation | Temps | Mesuré (MPa) | Prédit (MPa) | Erreur relative |
|---|---:|---:|---:|---:|
| R-PP1x | 30 j | 561,8 | 549,7 | 2,15 % |
| R-PP1x | 120 j | 555,8 | 537,7 | 3,26 % |
| R-PP3x | 30 j | 465,2 | 480,7 | 3,33 % |
| R-PP3x | 120 j | 454,9 | 470,4 | 3,41 % |
| R-PP3x + 3 % CHF | 30 j | 504,9 | 488,8 | 3,20 % |
| R-PP3x + 3 % CHF | 120 j | 488,8 | 478,0 | 2,20 % |
| R-PP3x + 5 % CHF | 30 j | 492,4 | 503,2 | 2,20 % |
| R-PP3x + 5 % CHF | 120 j | 481,6 | 492,4 | 2,25 % |

Indicateurs : MAE 13,72 MPa, RMSE 13,99 MPa, MAPE 2,75 %, R² 0,854. Les huit points sont couverts par la plus grande erreur interne, soit ±3,41 %.

Source primaire : *Effect of Natural Aging on the Properties of Recycled Polypropylene and Corn Husk Fiber Composites*, Polymers 16(13), 1788 (2024), DOI [10.3390/polym16131788](https://doi.org/10.3390/polym16131788).

## Cas 2 — composite caoutchouc butyle IIR/BRC

Les 21 valeurs viennent du tableau 2 de l’article, colonne `E exp`, en présence du fluide Milform 64 SST. Pour le test temporel, chaque point intérieur est retiré puis interpolé à partir des deux temps voisins.

| Température | Temps | Mesuré (MPa) | Prédit (MPa) | Erreur relative |
|---:|---:|---:|---:|---:|
| 80 °C | 1 h | 2,64 | 2,65 | 0,38 % |
| 80 °C | 2 h | 2,43 | 2,56 | 5,49 % |
| 80 °C | 4 h | 2,41 | 2,37 | 1,87 % |
| 80 °C | 6 h | 2,30 | 2,39 | 3,91 % |
| 80 °C | 14 h | 2,31 | 2,16 | 6,59 % |
| 100 °C | 1 h | 2,51 | 2,61 | 3,98 % |
| 100 °C | 2 h | 2,52 | 2,45 | 2,78 % |
| 100 °C | 4 h | 2,33 | 2,35 | 0,86 % |
| 100 °C | 6 h | 2,18 | 2,27 | 3,94 % |
| 100 °C | 14 h | 2,01 | 2,06 | 2,71 % |
| 120 °C | 1 h | 6,28 | 5,36 | 14,65 % |
| 120 °C | 2 h | 6,46 | 5,27 | 18,37 % |
| 120 °C | 4 h | 3,26 | 4,94 | 51,38 % |
| 120 °C | 6 h | 3,41 | 3,24 | 5,04 % |
| 120 °C | 14 h | 3,15 | 3,25 | 3,32 % |

Indicateurs temporels : MAE 0,321 MPa, RMSE 0,588 MPa, MAPE 8,35 %, R² 0,810. Treize points sur quinze sont compris dans la bande interne ±14,65 %. Le pic puis la chute à 120 °C rendent l’interpolation à 4 h impropre.

Le second contrôle masque toute la courbe à 100 °C et la reconstruit avec 80 et 120 °C. Il produit 11,31 % d’erreur moyenne, 28,76 % au maximum et un R² de -2,154. Materia utilise donc les courbes exactes à 80, 100 ou 120 °C et avertit l’utilisateur pour une température intermédiaire.

Source primaire : Nguyen-Tri, Triki et Nguyen, *Butyl Rubber-Based Composite: Thermal Degradation and Prediction of Service Lifetime*, Journal of Composites Science 3(2), 48 (2019), DOI [10.3390/jcs3020048](https://doi.org/10.3390/jcs3020048).

## Cas 3 — composite fibres de lin/époxy

Une campagne de température est cachée. Materia conserve son module initial et applique la rétention observée dans l’autre campagne. Les points intermédiaires sont numérisés depuis la figure 4a, avec une incertitude de lecture estimée à 3 %.

| Température cible | Temps | Mesuré (MPa) | Prédit (MPa) | Erreur relative |
|---:|---:|---:|---:|---:|
| 20 °C | 1 j | 24 400 | 24 000 | 1,64 % |
| 20 °C | 3 j | 17 800 | 17 400 | 2,25 % |
| 20 °C | 9 j | 12 700 | 11 400 | 10,24 % |
| 20 °C | 38 j | 12 000 | 11 200 | 6,67 % |
| 40 °C | 1 j | 24 000 | 24 400 | 1,67 % |
| 40 °C | 3 j | 17 400 | 17 800 | 2,30 % |
| 40 °C | 9 j | 11 400 | 12 700 | 11,40 % |
| 40 °C | 38 j | 11 200 | 12 000 | 7,14 % |

Indicateurs : MAE 725 MPa, RMSE 814 MPa, MAPE 5,41 %, R² 0,975 et erreur maximale 11,40 %.

Source primaire : Scida et al., *Influence of hygrothermal ageing on the damage mechanisms of flax-fibre reinforced epoxy composite*, Composites Part B 48, 51–58 (2013), DOI [10.1016/j.compositesb.2012.12.010](https://doi.org/10.1016/j.compositesb.2012.12.010).

## Valeur utilisable dans Materia

- Pour le PP H301 dans la fenêtre publiée, la courbe centrale peut servir de valeur de comparaison avant essais ; l’erreur interne observée est inférieure à 3,5 %.
- Pour l’IIR, il faut choisir la courbe exacte correspondant au fluide, à la formulation et à 80, 100 ou 120 °C. Une interpolation au voisinage du transitoire 120 °C n’est pas exploitable comme valeur de dimensionnement.
- Pour le lin/époxy, le transfert 20–40 °C est cohérent dans les 38 jours publiés, avec environ 5,4 % d’erreur moyenne dans ce corpus.
- Au-delà des temps mesurés, sur un autre grade ou dans un autre milieu, la courbe reste une extrapolation à confronter aux essais futurs.

Les calculs sont reproductibles sur la page **Validité** et par les routes `/api/validation/pp`, `/api/validation/iir` et `/api/validation/flax-epoxy`.
