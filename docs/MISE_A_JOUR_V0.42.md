# Materia v0.42 — calcul et plage uniformes

Le simulateur de fiches matériaux applique désormais la même convention à tous les matériaux.

## Règle commune

1. Materia calcule la courbe centrale avec les données les plus pertinentes disponibles pour le matériau.
2. La borne rapide applique `×1,20` à la vitesse de vieillissement centrale.
3. La borne lente applique `×0,80` à cette même vitesse.
4. Le temps central au seuil reste la valeur de travail recommandée.

Pour un temps central `t`, la plage affichée est donc :

- borne basse : `t / 1,20` ;
- borne haute : `t / 0,80`.

Cette convention donne la même ouverture relative pour chaque matériau : environ −16,7 % / +25 % autour du temps central. La largeur en MPa augmente progressivement avec le vieillissement et reste nulle au temps initial.

## Ce qui reste propre au matériau

La courbe centrale conserve les informations réelles disponibles : profil publié, module initial, famille, température, humidité, épaisseur et milieu. Appliquer une courbe centrale identique à tous les polymères supprimerait les différences physiques recherchées.

Les écarts-types publiés et les erreurs des validations PP, IIR et lin/époxy restent enregistrés dans la traçabilité scientifique et visibles sur la page **Validité**. Ils ne modifient plus la plage principale utilisée pour comparer les matériaux.

## Interprétation

La plage `×0,80–×1,20` est une sensibilité standardisée. Elle facilite une comparaison homogène entre matériaux, mais ne constitue pas un intervalle de confiance universel. La qualification finale d’un matériau exige toujours une comparaison avec une campagne expérimentale indépendante.
