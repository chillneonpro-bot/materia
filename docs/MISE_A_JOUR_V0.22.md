# Materia v0.22 — une valeur centrale et des limites explicites

La v0.22 répond à une difficulté de lecture : une grande enveloppe de sensibilité ne permet pas de choisir entre la borne basse, la valeur centrale et la borne haute.

## Règle de lecture

- La **courbe centrale** est la seule valeur à figer pour la future comparaison aveugle.
- Une bande issue d’un seul article décrit une dispersion interne au corpus. Elle n’est pas présentée comme un intervalle prédictif.
- Une borne basse ne pourra servir de valeur prudente qu’après vérification de sa couverture sur au moins trois sources indépendantes et compatibles.
- Quand aucune cinétique compatible n’existe, Materia conserve une ligne centrale exploratoire mais masque l’enveloppe arbitraire ÷3/×3. Aucune durée de vie exploitable n’est annoncée.

## Données IIR ajoutées

Le tableau 2 de l’article `10.3390/jcs3020048` est intégré : 24 valeurs expérimentales du module de Young et leurs écarts-types, à 80, 100 et 120 °C entre 0 et 24 h.

Le calcul fondé sur ces valeurs est activé uniquement si les conditions demandées sont compatibles :

- matériau IIR ;
- immersion dans Milform 64 SST ;
- température comprise entre 80 et 120 °C.

Il ne transfère pas ces mesures vers l’eau, vers un liquide non précisé, vers 23 °C ou vers une autre formulation.

## Garde-fous

- seules les lignes portant le statut `source_verified_table` peuvent alimenter le calcul ;
- la propriété doit être le module de Young ;
- le fluide est vérifié dans le moteur, pas seulement dans l’interface ;
- la méthode d’extraction et la formulation sont conservées dans la base ;
- un indicateur de correspondance documentaire décrit les informations couvertes et manquantes sans être présenté comme une probabilité de justesse.

## Validation logicielle

La suite comporte 85 tests. Elle vérifie notamment qu’une ligne non validée, une température hors domaine ou un liquide différent ne peuvent pas activer le profil publié.
