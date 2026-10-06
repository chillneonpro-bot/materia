# Materia v0.35 — planificateur d’expériences

## Plan automatique depuis une projection

La fiche matériau contient maintenant un volet **Planifier une campagne de validation**. L’utilisateur choisit :

- entre 5 et 10 temps distincts ;
- entre 3 et 20 éprouvettes par lot et par temps ;
- entre 1 et 8 lots indépendants.

Le plan couvre en priorité :

1. la référence initiale à `t = 0` ;
2. une mesure précoce ;
3. la fin de la fenêtre documentaire comparable ;
4. le franchissement central du seuil lorsqu’il tombe dans l’horizon ;
5. la valeur à l’horizon final.

Les temps supplémentaires sont classés avec un score heuristique combinant la largeur de la bande, la pente de la courbe et la couverture temporelle. Ce score sert seulement à classer les mesures : il ne promet aucun pourcentage de réduction de l’incertitude.

## Organisation de la campagne

Avec au moins deux lots, le dernier lot est signalé comme **lot de validation aveugle réservé**. Materia recommande de conserver ce lot fermé jusqu’au gel de la prédiction. L’ordre des éprouvettes doit être randomisé et chaque valeur brute doit garder son identifiant.

Le plan reste disponible dans les projets enregistrés et peut être recalculé avec un autre nombre de temps, de lots ou de répétitions.

## Classeur laboratoire

L’export Excel comporte quatre feuilles :

- **Plan de campagne** : calendrier proposé, prévisions, bornes et graphique ;
- **Éprouvettes** : une ligne par éprouvette avec identifiant, lot, temps et champs de saisie ;
- **Import validation** : colonnes `time_days`, `modulus_mpa` et `replicate_id`, compatibles avec la page Validation aveugle ;
- **Méthode et traçabilité** : protocole, limites, modèle et empreinte du résultat.

La suite contient 114 tests. Elle contrôle les temps obligatoires, l’espacement d’une campagne courte, le calcul des effectifs, le caractère déterministe du plan, les bornes des paramètres et les quatre feuilles du classeur.
