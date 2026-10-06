# Materia v0.26 — une estimation claire avant essais

## Résultat à utiliser

Pour chaque matériau, Materia affiche à nouveau une courbe centrale et un temps central de franchissement du seuil. Cette ligne centrale est la **valeur de travail recommandée** pour préparer une comparaison future avec des expériences.

Le logiciel ne demande plus à l'utilisateur de choisir entre trois scénarios. Les bornes servent uniquement à montrer la sensibilité du résultat si le grade réel vieillit un peu plus vite ou un peu plus lentement que la famille documentaire.

## Plage générique resserrée

L'ancienne variation de vitesse ÷3 à ×3 produisait une enveloppe trop large et peu exploitable. Pour les matériaux sans série temporelle compatible, la version 0.26 utilise :

- vitesse centrale : ×1,00 ;
- vieillissement plus rapide : ×1,50 ;
- vieillissement plus lent : ×0,65.

La largeur du temps au seuil vaut ainsi environ un facteur 2,31 entre les deux bornes, au lieu d'un facteur 9. Cette plage est une analyse de sensibilité documentaire. Elle n'a pas de couverture probabiliste annoncée.

## Cas mieux documentés

Le PP en exposition naturelle conserve un traitement distinct : la courbe centrale est une médiane inter-publications et la bande P10–P90 pilote est calibrée en retirant successivement chacune des trois publications. Dans ce cas, la P50 est la valeur à figer avant essais.

Pour l'IIR dans Milform 64 SST entre 80 et 120 °C, Materia interpole les courbes et écarts-types publiés dans leur domaine. En dehors de ce domaine, il revient à l'estimation de famille.

## Lecture de l'interface

La première carte donne la valeur centrale à utiliser. La deuxième donne la plage de sensibilité ou l'intervalle pilote selon le niveau de preuve. La troisième donne le module prédit à l'horizon demandé. La courbe, le tableau, les exports Excel, PDF et JSON utilisent exactement les mêmes valeurs et conservent l'empreinte des paramètres.

Cette version répond au besoin d'une prévision avant essais tout en conservant une distinction visible entre estimation de famille et prédiction soutenue par plusieurs publications.
