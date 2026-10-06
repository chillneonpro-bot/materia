# Materia v0.27 — extrapolation PP cohérente et exploitable

La version 0.27 corrige une contradiction visible lorsque l'horizon PP dépassait 120 jours : la courbe centrale franchissait le seuil, mais la carte indiquait seulement « Non atteint » parce que ce franchissement se trouvait après la fenêtre publiée.

Materia affiche maintenant :

- le temps central estimé au seuil, même lorsqu'il se situe après la fenêtre publiée ;
- la mention explicite « extrapolation après 120 jours » ;
- la plage de sensibilité associée à ce temps ;
- la P50 comme valeur de travail à comparer aux essais futurs.

Le P10–P90 pilote n'est plus prolongé sur plusieurs années. Sa couverture a été évaluée uniquement sur la fenêtre commune de 0 à 120 jours. Pour un horizon plus long, la courbe centrale est prolongée et la zone affichée module sa dégradation cumulée de ×0,65 à ×1,50. Cette zone est une sensibilité d'extrapolation, sans interprétation probabiliste.

Pour le scénario PP de la fiche standard, à 23 °C, 50 % HR, 2 mm et en extérieur :

- P50 à deux ans : environ 533 MPa ;
- estimation centrale du seuil de 80 % : environ 8 mois ;
- sensibilité du temps au seuil : environ 5 mois à 1 an ;
- sensibilité du module à deux ans : environ 371 à 687 MPa.

Le calcul, le graphique, les tableaux et les exports partagent les mêmes valeurs.
