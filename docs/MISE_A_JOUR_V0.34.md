# Materia v0.34 — deux lectures de la dispersion

## Bande centrale et extrêmes observés

Lorsqu’une projection repose sur un corpus compatible, la page **Fiche matériau** propose deux affichages :

- **Bande centrale recommandée** : P10–P90 pilote calibré hors publication, quartiles inter-formulations ou sensibilité d’extrapolation selon le domaine ;
- **Enveloppe complète min–max observée** : valeurs extrêmes des courbes du corpus, limitées à la fenêtre temporelle commune.

Le min–max n’est jamais prolongé après la dernière observation comparable. Sur un horizon long, la zone s’arrête donc à la ligne **Fin des observations comparables**, tandis que la courbe centrale continue avec son statut d’extrapolation.

Le min–max observé peut être plus étroit que le P10–P90 pilote. Le premier décrit les extrêmes du corpus disponible ; le second provient des erreurs obtenues en laissant une publication entière de côté. Materia les présente donc comme deux informations différentes.

## Export et contrôles

Le classeur Excel ajoute les colonnes **Minimum observé du corpus** et **Maximum observé du corpus**. Les cellules restent vides hors de la fenêtre publiée et le graphique Excel affiche les deux courbes en pointillé.

La suite comporte maintenant 110 tests. Elle contrôle la coupure de l’enveloppe à la fin des observations, les libellés du graphique et la présence des deux colonnes dans l’export.
