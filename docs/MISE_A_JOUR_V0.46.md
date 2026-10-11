# Materia v0.46 — navigation et essais réels

Date : 11 octobre 2026.

## Interface

Le menu **Ressources** est maintenant un bouton ouvrant un menu contextuel. Il reste accessible depuis toutes les pages et conserve l’indication de la section active.

## Données IIR corrigées

Les 21 modules IIR ont été retranscrits depuis le tableau 2 de la publication, qui correspond aux essais en présence du fluide Milform 64 SST. L’ancienne série provenait du tableau sans fluide et ne correspondait pas au milieu annoncé dans l’interface.

La correction est propagée dans la base, le calcul, les avertissements, les tests et la page **Validité**.

## Comparaison mesuré / prédit

Le rapport [`COMPARAISON_ESSAIS_REELS_V0.46.md`](COMPARAISON_ESSAIS_REELS_V0.46.md) regroupe les résultats point par point pour le PP H301, l’IIR/BRC et le lin/époxy. Il sépare la plage visuelle commune de 10 % des erreurs scientifiques effectivement observées pendant les validations masquées.
