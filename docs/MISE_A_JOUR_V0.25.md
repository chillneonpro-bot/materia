# Materia v0.25 — résultats exploitables clairement séparés

## Problème corrigé

Une fiche matériau dépourvue de série de vieillissement compatible affichait encore une courbe centrale générique, une date de seuil et une sensibilité de vitesse divisée ou multipliée par trois. Malgré les avertissements, ces chiffres ressemblaient à des résultats utilisables.

## Nouvelle règle

Si aucune cinétique temporelle vérifiée du module de Young ne correspond au matériau et au milieu sélectionnés, Materia affiche désormais **Aucun modèle prédictif disponible**. Il ne montre plus :

- la courbe générique ;
- la valeur à l’horizon ;
- le temps au seuil ;
- la plage ÷3/×3 ;
- les commandes de gel et d’export d’une prédiction.

La page explique la donnée manquante et permet de charger directement l’un des deux domaines documentaires disponibles.

## Résultat PP à utiliser

Pour le PP en exposition extérieure et un horizon maximal de 120 jours, les trois cartes indiquent maintenant :

1. la prévision centrale P50 en MPa et en pourcentage conservé ;
2. les bornes P10–P90 en MPa au même horizon ;
3. si le seuil est réellement franchi dans la fenêtre publiée.

Le logiciel ne présente plus une date de seuil obtenue au-delà des 120 jours observés. À 120 jours avec E₀ = 1 100 MPa, la valeur centrale est d’environ 990 MPa, soit 90 % conservés. La P50 est la courbe à figer pour la future comparaison aveugle. La bande P10–P90 reste pilote.

## Hors domaine temporel

Si l’horizon demandé dépasse la fenêtre publiée, la projection est bloquée. Materia propose de revenir automatiquement à la dernière durée documentée au lieu de présenter une extrapolation comme exploitable.

## Domaines disponibles

- PP, extérieur / UV : 0–120 jours, P50 documentaire et P10–P90 pilote issus de trois publications ;
- IIR, Milform 64 SST : 80–120 °C et 0–24 h, interpolation du tableau publié avec son écart-type.

## Vérification

La suite comporte 95 tests. Le parcours navigateur vérifie qu’un matériau non calibré n’affiche aucun graphique ni bouton de gel, puis que le bouton PP charge une courbe P50 et réactive le gel de la prédiction.
