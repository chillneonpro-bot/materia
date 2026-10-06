# Materia v0.36 — vue par lot et par éprouvette

La validation après essais conserve désormais chaque valeur brute avec son **lot** et son **identifiant d’éprouvette**. L’utilisateur obtient trois niveaux de lecture : résultat global de la campagne, dispersion par lot et par temps, puis détail de chaque éprouvette.

## Détection documentée des valeurs atypiques

Materia dépiste les valeurs atypiques séparément dans chaque groupe `lot × temps` :

- au moins cinq éprouvettes sont nécessaires pour un dépistage automatique ;
- la règle principale utilise le score z modifié fondé sur la médiane et la MAD, avec le seuil `|z| > 3,5` ;
- lorsque la MAD est nulle, une règle de Tukey fondée sur l’IQR est utilisée ; si la MAD et l’IQR sont toutes deux nulles, seul un écart relatif supérieur à 5 % de la médiane est signalé afin d’éviter les faux positifs dus à l’arrondi ;
- si le groupe est trop petit, le logiciel affiche **Non évalué** au lieu de conclure ;
- une valeur signalée reste incluse dans la moyenne et dans les métriques de validation.

Un signalement demande donc une vérification de la saisie, de l’éprouvette et du protocole. Il ne constitue jamais une autorisation de supprimer automatiquement la mesure.

## Interface et exports

La page **Contrôle après essais** affiche :

- le nombre de lots et d’éprouvettes ;
- les groupes évaluables et ceux qui sont trop petits ;
- moyenne, écart-type, coefficient de variation, médiane, minimum et maximum par lot et par temps ;
- le statut et la justification de chaque éprouvette ;
- un graphique des valeurs brutes distingué par lot.

Le classeur de validation contient maintenant cinq feuilles : **Bilan**, **Prédiction et mesures**, **Lots**, **Éprouvettes** et **Traçabilité**. Le modèle Excel et le plan d’expérience utilisent les colonnes `time_days`, `modulus_mpa`, `replicate_id`, `lot_id` et `specimen_id`.

## Validation logicielle

La suite comporte **120 tests**. Elle vérifie notamment la séparation des lots, le seuil robuste, le refus de conclure sur les petits groupes, le maintien des points signalés dans les métriques, la prévention des faux positifs d’arrondi et les nouvelles feuilles Excel.
