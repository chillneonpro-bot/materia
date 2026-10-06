# Materia v0.15 — premier corpus scientifique accepté

## Données relues

- 10 points du composite lin/époxy de Scida et al. acceptés après comparaison avec le PDF primaire et la figure 4a ;
- deux expériences : 20 et 40 °C, 90 % HR, plaque de 2,5 mm, cinq temps de 0 à 38 jours ;
- 12 moyennes MDPI du PP, avec écarts-types et `n=7`, classées comme valeurs de tableau vérifiées sous licence CC BY 4.0 ;
- source, emplacement, protocole, relecteur, date et justification conservés.

## Correction de qualité

La publication Scida indique une mesure à température ambiante, sans valeur exacte. La valeur `23 °C` auparavant utilisée a été supprimée. Le schéma accepte maintenant explicitement cette information inconnue au lieu d’inventer une valeur.

## Garde-fous

Les points Scida autorisent uniquement une interpolation entre les temps observés, aux conditions exactes. L’extrapolation au-delà de 38 jours reste refusée. L’entraînement est bloqué car le corpus ne contient que 10 points et deux expériences, contre un minimum de 12 points et trois expériences.

Les valeurs MDPI autorisent uniquement la lecture et l’interpolation entre 0, 30 et 120 jours pour les formulations publiées. Elles ne sont pas converties artificiellement en exposition à température et humidité constantes.

## Validation logicielle

Les 58 tests automatisés réussissent. Une sauvegarde vérifiée a été créée avant la promotion du corpus.
