# Materia v0.20 — audit du modèle PP et incertitudes

## Modèle PP corrigé

L’ancienne extrapolation exponentielle ajustée sur 0 et 30 jours surestimait fortement la perte à 120 jours. La v0.20 compare cinq méthodes en laissant chaque formulation de côté à son tour. Le modèle retenu sépare la phase initiale et la phase tardive : il utilise E₀ et E₃₀ du grade cible, puis apprend le ralentissement sur les formulations restantes.

Dans le corpus actuel, la MAE passe à 3,83 MPa et la MAPE à 0,77 %, contre 99,90 MPa et 20,33 % pour l’exponentielle. Ce résultat reste interne à quatre formulations d’une seule publication.

## Intervalles mieux définis

- Les mesures publiées proposent la dispersion des éprouvettes ou l’IC95 % de la moyenne, avec leur différence expliquée.
- Le calculateur E₀/E₃₀ → E₁₂₀ affiche une enveloppe empirique interne de ±1,98 %.
- La projection PP issue d’une fiche affiche les quartiles 25–75 % des profils comme zone centrale et conserve le min–max complet dans le manifeste.
- Le graphique marque la fin des observations comparables et colore la zone extrapolée.
- Au-delà de trois fois la fenêtre observée, le niveau de preuve est automatiquement ramené au niveau 1.

## Centre de validité

Le centre présente maintenant le benchmark complet, un calculateur à 120 jours et les six failles scientifiques encore ouvertes. Une source indépendante non compatible reste documentée et exclue du score.

## Audit et feuille de route

Le document `docs/AUDIT_COMPLET_V0.20.md` couvre les données, les biais, les risques de transfert, le plan expérimental, les critères de validation, l’exploitation en école et les priorités UX.

## Statut

Materia v0.20 est un outil pédagogique et un pilote de préparation d’essais. Aucun résultat n’est présenté comme une durée de vie qualifiée. La prochaine étape scientifique décisive est une campagne PP indépendante, avec lots réservés et valeurs brutes par éprouvette.

## Vérification de livraison

- 77 tests automatisés réussis ;
- aucune dépendance Python cassée ;
- routes santé, matériaux, validation, simulation et comparaison en HTTP 200 ;
- contrôle visuel du centre de validité et de la projection hors domaine ;
- sonde locale de 30 utilisateurs, 90 requêtes et zéro erreur ;
- sauvegarde `data/backups/materia-v0.20.zip` créée et vérifiée.
