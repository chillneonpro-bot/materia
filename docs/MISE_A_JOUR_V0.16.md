# Materia v0.16 — maturité scientifique et incertitude lisible

## Diagnostic par matériau

La page **Données et modèles → Modèles et maturité** affiche maintenant :

- le nombre de points et d'expériences acceptés face au seuil logiciel ;
- les blocages qui interdisent encore l'évaluation d'un modèle ;
- la campagne expérimentale minimale recommandée ;
- la nature exacte de l'incertitude disponible ;
- les publications candidates qui demandent encore une extraction ou qui mesurent une autre propriété.

Pour le composite lin/époxy, la priorité est une troisième campagne indépendante à 30 °C, 90 % HR et 2,5 mm, avec au moins cinq éprouvettes par temps et conservation des répétitions brutes. Cette recommandation est un plan d'essai ; elle n'est pas une donnée mesurée.

## Incertitude

Les mesures PP proposent deux lectures distinctes :

- **±1 écart-type** : dispersion observée entre les sept éprouvettes ;
- **IC95 % de la moyenne** : précision statistique de la moyenne, plus étroite, sans prétendre décrire une nouvelle éprouvette.

La bande lin/époxy est explicitement identifiée comme une incertitude de numérisation estimée. Elle ne couvre ni la dispersion entre éprouvettes, ni les lots, ni l'erreur prédictive.

## Nouvelles sources qualifiées

- PP/Opoka, DOI `10.3390/ma15010338` : module de Young relatif sous vieillissement accéléré, extraction de la figure encore requise ;
- iPP vieilli naturellement, DOI `10.3390/polym12122828` : campagne pertinente pour le contexte, mais propriété temporelle principale incompatible avec la cible actuelle, car il s'agit de résistance en traction.

Ces deux sources restent hors du corpus de calcul jusqu'à ce qu'elles satisfassent les exigences de propriété, de conditions et de traçabilité.

## Contrôles

- 59 tests automatisés réussis ;
- routes de santé et API matériau vérifiées ;
- parcours visuel contrôlé pour le diagnostic lin/époxy et les deux bandes PP ;
- sauvegarde v0.16 créée et vérifiée.
