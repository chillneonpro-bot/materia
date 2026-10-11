# Validation masquée de deux matériaux supplémentaires — Materia v0.41

Date de l’étude : 9 octobre 2026.

## Objectif

Cette étude vérifie la capacité de Materia à reconstruire des valeurs publiées qui lui sont volontairement cachées. Elle porte sur deux matériaux différents du PP H301 :

- un composite de caoutchouc butyle chargé de noir de carbone, immergé dans le fluide Milform 64 SST à 80, 100 et 120 °C ;
- un composite quasi unidirectionnel fibres de lin/époxy vieilli à 90 % HR à 20 et 40 °C.

Les résultats sont internes aux publications citées. Ils ne prouvent pas encore le transfert à un autre grade, un autre lot, une autre géométrie ou un autre milieu.

## Correction du corpus IIR

Le corpus antérieur provenait d’une lecture OCR erronée. Il a été remplacé par la transcription directe des 21 valeurs `E_exp` du tableau 2 de l’article primaire, mesurées en présence du fluide Milform 64 SST. Les temps exacts sont 0, 1, 2, 4, 6, 14 et 24 h. Le faux temps 3 h a été supprimé.

Source : Nguyen-Tri, Triki et Nguyen, *Butyl Rubber-Based Composite: Thermal Degradation and Prediction of Service Lifetime*, Journal of Composites Science 3(2), 48 (2019), DOI [10.3390/jcs3020048](https://doi.org/10.3390/jcs3020048).

## IIR : validation temporelle masquée

Chaque point intérieur est retiré à tour de rôle. Materia le reconstruit par interpolation linéaire entre les deux temps publiés qui l’encadrent, à température constante.

| Indicateur | Résultat |
|---|---:|
| Prédictions masquées | 15 |
| MAE | 0,321 MPa |
| RMSE | 0,588 MPa |
| MAPE | 8,35 % |
| R² | 0,810 |
| Bande conformale interne cible 80 % | ±14,65 % |
| Couverture empirique | 86,67 % |
| Pire erreur relative | 51,38 % |

La bande interne ±14,65 % couvre 13 des 15 points masqués. Elle ne couvre pas le transitoire brutal de la courbe à 120 °C entre 2 h et 4 h, où l’interpolation atteint 51,38 % d’erreur. Materia doit donc restituer les points publiés exacts à cette température et signaler qu’une interpolation traversant ce transitoire est peu fiable.

## IIR : transfert en température

La courbe complète à 100 °C est ensuite masquée. La prédiction utilise seulement son module initial et l’interpolation des rétentions mesurées à 80 et 120 °C.

| Indicateur | Résultat |
|---|---:|
| Prédictions masquées | 6 |
| MAE | 0,278 MPa |
| MAPE | 11,31 % |
| R² | -2,154 |
| Pire erreur relative | 28,76 % |

Le transfert linéaire en température est rejeté. Le R² négatif signifie que cette reconstruction est moins pertinente qu’une moyenne constante des valeurs à 100 °C. Materia privilégie donc les courbes publiées exactes à 80, 100 ou 120 °C. Une température intermédiaire reçoit une alerte et une borne scientifique de ±28,76 % issue de ce test masqué.

## Lin/époxy : transfert entre deux campagnes

Chaque campagne est cachée à tour de rôle. Materia conserve le module initial de la campagne cible et applique la rétention de l’autre température aux jours 1, 3, 9 et 38.

| Indicateur | Résultat |
|---|---:|
| Prédictions masquées | 8 |
| MAE | 725 MPa |
| RMSE | 814 MPa |
| MAPE | 5,41 % |
| R² | 0,975 |
| Bande conformale interne cible 80 % | ±11,40 % |
| Couverture empirique | 100 % |
| Pire erreur relative | 11,40 % |

La bande ±11,4 % est retenue comme bande pilote dans la fenêtre 0–38 jours pour la formulation exacte de l’article. Les valeurs intermédiaires proviennent d’une numérisation de figure estimée à ±3 %. Cette incertitude de lecture est distincte de la variabilité réelle des éprouvettes, qui n’est pas disponible sous forme brute.

Source : Scida et al., *Influence of hygrothermal ageing on the damage mechanisms of flax-fibre reinforced epoxy composite*, Composites Part B 48, 51–58 (2013), DOI [10.1016/j.compositesb.2012.12.010](https://doi.org/10.1016/j.compositesb.2012.12.010).

## Décision d’utilisation

| Cas | Courbe recommandée | Bande | Limite |
|---|---|---:|---|
| IIR à 80, 100 ou 120 °C | Courbe publiée exacte | Écart-type publié | 0–24 h, Milform 64 SST, formulation BRC de l’article |
| IIR entre deux temps mesurés | Interpolation temporelle hors transitoire brutal | ±14,7 % pilote | Pire erreur observée 51,4 % à 120 °C / 4 h |
| IIR à une température non publiée | Ne pas annoncer la même précision | au moins ±28,8 % dans ce test | Loi thermique non validée |
| Lin/époxy 20–40 °C | Rétention transférée | ±11,4 % pilote | 0–38 jours, 90 % HR, formulation exacte |

Les calculs reproductibles sont disponibles sur la page **Validité**, ainsi que par les routes `/api/validation/iir` et `/api/validation/flax-epoxy`.
