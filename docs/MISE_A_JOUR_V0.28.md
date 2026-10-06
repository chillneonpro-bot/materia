# Materia v0.28 — comparateur vérifié et axes cohérents

La version 0.28 corrige une erreur d'échelle possible lors de la comparaison de résultats enregistrés avec des unités différentes. Auparavant, une courbe affichée en années et une autre en jours pouvaient conserver leurs valeurs numériques propres sur un axe dont le libellé dépendait de la dernière courbe.

Toutes les courbes sont maintenant converties en jours en interne, puis affichées dans une unité commune : jours, mois ou années. Dans le comparateur de matériaux, l'unité choisie par l'utilisateur est respectée. Dans les projets enregistrés, Materia sélectionne automatiquement une unité adaptée à l'horizon le plus long.

Le comparateur affiche désormais :

- un axe temporel commun ;
- un seuil commun lorsqu'il est identique entre les scénarios ;
- le module initial et le module final en MPa ;
- la conservation relative en pourcentage ;
- le temps central au seuil ;
- le niveau de preuve de chaque matériau ;
- l'horizon propre à chaque simulation enregistrée.

La cohérence numérique a été contrôlée sur les 50 matériaux, en intérieur, extérieur et immersion, soit 150 scénarios. Aucun résultat non fini, aucune borne inversée et aucune erreur de calcul n'ont été détectés.

Les trois parcours ont été vérifiés : matériaux réels, exercice synthétique A/B/C et simulations enregistrées. Les exports Excel utilisent déjà les jours comme unité commune et restent cohérents avec l'écran.
