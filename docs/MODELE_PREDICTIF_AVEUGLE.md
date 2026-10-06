# Modèle prédictif aveugle de vieillissement

## Objectif

Materia doit produire une courbe avant de connaître les futurs essais de l’utilisateur. Cette courbe est ensuite figée, puis comparée aux mesures réelles sans réajustement rétrospectif. Cette procédure mesure honnêtement la capacité de généralisation du modèle.

## Ce que « données matériau » doit contenir

Le module initial ne détermine pas une vitesse de vieillissement. Le modèle doit utiliser :

- polymère, grade et formulation ;
- charges, fibres, pigments, plastifiants et stabilisants connus ;
- procédé, cristallinité, réticulation et conditionnement ;
- géométrie et épaisseur ;
- propriété et protocole de mesure ;
- température et humidité dans le temps ;
- UV ou dose radiative ;
- nature du liquide, pH et oxygène dissous en immersion ;
- contrainte mécanique éventuelle ;
- courbes publiées comparables.

Ces informations peuvent provenir de fiches techniques, de publications et de bases documentaires. Aucun essai de l’utilisateur n’est requis pour produire la première prédiction.

## Algorithme cible

1. Rechercher les études compatibles avec le matériau, la propriété et le milieu.
2. Normaliser les propriétés sous forme `E(t)/E0` sans mélanger module, résistance et allongement.
3. Calculer un score de proximité sur le grade, la formulation, le procédé, le protocole, le milieu et la température.
4. Ajuster un modèle hiérarchique par mécanisme et par étude. Les études proches contribuent davantage, mais l’effet « étude » reste séparé de l’effet « formulation ».
5. Comparer plusieurs lois : profil par morceaux, Weibull avec période d’induction, modèle semi-paramétrique et modèle physique lorsque ses paramètres sont identifiables.
6. Sélectionner et calibrer le modèle en laissant successivement une étude entière de côté. Une formulation du même article ne compte pas comme validation externe.
7. Produire la médiane prédictive P50 et un intervalle prédictif P10–P90 calibré sur les erreurs hors étude.
8. Refuser ou élargir la prédiction lorsqu’un changement de mécanisme ou une extrapolation excessive est détecté.

## Valeur à utiliser

- **P50** : prévision centrale à confronter aux essais futurs ;
- **P10 du temps de seuil** : scénario prudent pour une présélection, seulement si la couverture a été validée ;
- **P90 du temps de seuil** : scénario favorable, jamais une valeur de dimensionnement ;
- **P10–P90** : incertitude prédictive, dont la couverture doit être contrôlée sur des études indépendantes.

L’utilisateur ne choisit plus entre une vitesse arbitraire ×3, ×1 ou ÷3.

## Score de correspondance

Le logiciel doit publier séparément :

- correspondance matériau et formulation ;
- correspondance du milieu ;
- correspondance de température ;
- correspondance du protocole et de la propriété ;
- distance d’extrapolation temporelle ;
- nombre d’études et de formulations indépendantes ;
- erreur observée pendant la validation hors étude.

Une note élevée ne remplace pas l’erreur de validation. Elle explique seulement pourquoi les sources ont été retenues.

## Validation aveugle

Le fichier `materia-blind-prediction-v1` conserve la courbe centrale, ses bornes, les entrées, les sources, la date de coupure documentaire et une empreinte SHA-256. Toute modification ultérieure invalide cette empreinte. La structure complète de la courbe est aussi contrôlée : temps strictement croissant, mêmes longueurs, valeurs finies et courbe centrale comprise entre les bornes.

Après les essais, Materia calcule :

- MAE et RMSE en MPa ;
- MAPE ;
- biais signé ;
- couverture de l’intervalle P10–P90 ;
- erreur sur le temps de franchissement lorsqu’il est observé.

Pour une première campagne, les objectifs internes sont au moins cinq temps distincts, une MAPE au plus égale à 10 % et un biais absolu moyen au plus égal à 5 % de la moyenne observée. Les répétitions sont conservées individuellement, puis moyennées à chaque temps avec leur écart-type. Chaque temps reçoit ainsi le même poids dans le score, quel que soit le nombre d’éprouvettes. Les atteindre qualifie seulement la courbe centrale sur cette campagne. La généralisation exige au moins trois campagnes indépendantes ; la couverture d’une bande n’est évaluée que si cette bande avait été déclarée prédictive avant les essais.

La page de validation importe un CSV ou un classeur Excel avec `time_days`, `modulus_mpa` et, si possible, `replicate_id`. Elle superpose les moyennes expérimentales et leurs écarts-types à la courbe figée, puis exporte un classeur comprenant verdict, métriques, graphique, paramètres et empreinte du fichier gelé.

Le modèle ne doit être réajusté qu’après publication du rapport aveugle de la version précédente.

## État du corpus

- PP extérieur : six séries issues de trois publications indépendantes, avec une fenêtre commune de 120 jours. Une publication fournit un tableau exact et deux des figures numérisées avec incertitude d’extraction. Le P10–P90 pilote est calibré en laissant une publication entière de côté ; l’hétérogénéité des grades et climats garde la bande large.
- IIR : une source ouverte qualifiée documente un composite butyle dans un fluide d’usinage entre 80 et 120 °C. Elle ne permet pas une extrapolation directe vers un liquide non précisé à 23 °C.
- Autres familles : fiches documentaires disponibles, mais corpus temporel encore insuffisant pour calibrer des intervalles prédictifs.

## Critère de mise en service

Une famille passe en mode prédictif pilote lorsque le corpus contient au moins trois études indépendantes, plusieurs formulations et une validation hors étude avec une erreur et une couverture publiées. Le passage à une validation robuste exige davantage d’études compatibles et une validation prospective sur plusieurs campagnes ; trois sources constituent un minimum de calcul, pas une preuve industrielle.
