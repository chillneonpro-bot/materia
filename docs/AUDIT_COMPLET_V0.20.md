# Audit complet du modèle et de l’expérience utilisateur — Materia v0.20

Date de l’audit : 30 septembre 2026  
Périmètre : modèle PP, données, incertitudes, logiciel Python, usage pédagogique et préparation au déploiement.

## Verdict

Materia est utilisable comme outil pédagogique, comme visionneuse de mesures publiées et comme support pour préparer des essais. Il ne peut pas encore fournir une durée de vie qualifiée d’un polymère à partir de sa seule fiche technique.

La v0.20 corrige la faiblesse numérique la plus visible du modèle PP. L’ancienne loi exponentielle prolongeait la perte des 30 premiers jours et donnait, lors d’un test interne à 120 jours, une erreur relative moyenne de 20,33 %. Le nouveau modèle en deux phases utilise la mesure du grade cible à 30 jours et apprend le ralentissement 30–120 jours uniquement sur les autres formulations. Son erreur interne descend à 0,77 %, soit 3,83 MPa, et les quatre prédictions se situent dans l’écart-type publié. Cette amélioration est réelle dans le corpus, mais elle ne constitue pas une validation externe : les quatre formulations proviennent du même article.

Le résultat scientifique défendable est donc : **bon estimateur interne à court terme pour ces formulations PP, après une mesure à 30 jours ; transfert vers un autre grade, climat ou horizon non démontré**.

## Données réellement disponibles

| Élément | État | Conséquence |
|---|---:|---|
| Fiches documentaires | 50 matériaux | Utiles pour rechercher et préparer une étude, insuffisantes pour apprendre une cinétique |
| Corpus PP vérifié | 4 formulations, 0/30/120 jours, n = 7 | Permet une interpolation et un contrôle interne à court terme |
| Corpus lin/époxy accepté | 10 points, conditions limitées | Permet une interpolation descriptive dans son domaine exact |
| Campagne PP externe compatible | 0 | Empêche toute revendication de validation indépendante |
| Données brutes par éprouvette | absentes pour le PP | Empêche de séparer correctement erreur de mesure, lot et modèle |
| Historique T/HR/UV/oxygène | incomplet | Empêche de construire une dose environnementale transférable |

Une fiche matériau donne une propriété initiale dans des conditions données. Elle ne contient généralement ni la vitesse de photo-oxydation, ni la période d’induction, ni l’effet propre des stabilisants, ni la variabilité entre lots. Elle ne suffit donc pas à calculer une durée de vieillissement.

## Benchmark du modèle PP

Protocole : pour chaque formulation testée, seules ses valeurs à 0 et 30 jours sont visibles. Le paramètre de ralentissement est calculé sur les trois formulations restantes. La valeur à 120 jours sert uniquement au test.

| Méthode | MAE (MPa) | MAPE | R² | Erreur relative maximale |
|---|---:|---:|---:|---:|
| Deux phases, transfert hiérarchique | 3,83 | 0,77 % | 0,981 | 1,98 % |
| Palier après 30 jours | 10,80 | 2,22 % | 0,906 | 3,29 % |
| Rétention médiane des autres formulations | 13,81 | 2,78 % | 0,855 | 3,41 % |
| Exponentiel 0–30 jours | 99,91 | 20,33 % | −6,47 | 25,45 % |
| Linéaire 0–30 jours | 120,38 | 24,54 % | −9,93 | 31,83 % |

L’enveloppe ±1,98 % proposée par le calculateur 0/30 → 120 jours est l’erreur maximale constatée dans ce petit test interne. Elle n’est ni un intervalle de confiance universel ni un intervalle prédictif externe.

## Politique d’incertitude

Un intervalle plus serré n’est utile que s’il reste correctement calibré. La v0.20 applique quatre règles :

1. Sur une formulation publiée exacte, l’écart-type décrit la dispersion des éprouvettes. L’IC95 % de la moyenne décrit la précision de la moyenne. Aucun des deux ne couvre un futur grade.
2. Dans le calculateur PP avec E₀ et E₃₀, la bande ±1,98 % est une enveloppe empirique interne sur quatre erreurs hors formulation.
3. Pour une projection issue d’une fiche PP, la bande affichée est la zone interquartile des quatre profils normalisés, soit les 50 % centraux du corpus. L’enveloppe min–max complète est conservée dans le résultat.
4. Après le dernier temps observé, la zone devient une enveloppe de scénarios et non un intervalle statistique validé. Au-delà de trois fois la fenêtre de preuve, le résultat est rétrogradé au niveau 1.

Cette politique resserre la lecture dans le domaine observé sans masquer les risques de transfert. Une future bande à 80 % ou 90 % devra être calibrée sur des campagnes indépendantes par une méthode de prédiction appropriée, par exemple une calibration conformelle, après gel du modèle.

## Failles scientifiques et statistiques

### Critiques

| Faille | Risque | Correction requise |
|---|---|---|
| Aucune validation externe compatible | Le score de 0,77 % peut refléter la similarité des formulations d’un seul article | Réserver une campagne, un lot, un site et une période jamais utilisés pendant le développement |
| Transfert de grade non démontré | Additifs, pigments, charges, procédé et cristallinité changent la cinétique | Identifier le grade, la formulation, le procédé, le lot et le conditionnement ; exiger une ancre à 30 jours |
| Facteur Q10 non ajusté | Une accélération arbitraire peut déplacer fortement la durée estimée | Estimer l’énergie d’activation sur plusieurs températures et vérifier que le mécanisme ne change pas |
| Climat résumé par des valeurs fixes | Deux climats ayant la même moyenne peuvent produire des doses très différentes | Importer les séries horaires T, HR, UV, pluie et cycles ; construire des variables de dose |
| Seuil de module confondu avec fin de vie | Un module stable ou croissant peut accompagner une fragilisation | Définir la défaillance selon l’usage et suivre aussi résistance, allongement et ténacité |

### Hautes

- Trois temps seulement masquent une période d’induction, un changement de pente ou un mécanisme tardif.
- Quatre formulations ne suffisent pas pour estimer de façon fiable une distribution entre grades.
- Les moyennes et écarts-types ne permettent pas une modélisation hiérarchique complète sans valeurs individuelles.
- Les corrélations entre mesures d’une même éprouvette ou d’un même lot sont inconnues.
- L’exposition naturelle de la publication n’est pas une entrée climatique transférable vers une autre ville ou une autre année.
- Les facteurs génériques de famille utilisés hors PP sont des hypothèses pédagogiques, pas des paramètres mesurés.
- Le modèle impose une dégradation monotone alors que post-cristallisation, séchage ou réticulation peuvent augmenter temporairement le module.
- Les pièces épaisses et films minces ne suivent pas forcément la même limitation par diffusion d’oxygène.

### Modélisation et apprentissage automatique

- Le module ML hygrothermique doit rester désactivé pour la prédiction tant que moins de 12 expériences et trois conditions distinctes ne sont pas acceptées ; ce seuil est un minimum logiciel, pas une garantie scientifique.
- Une sélection du meilleur modèle sur les mêmes groupes que ceux servant à annoncer sa performance produit un biais optimiste.
- Les importances calculées sur le corpus d’apprentissage n’établissent pas une causalité.
- Les données censurées, les valeurs sous seuil et les éprouvettes perdues ne sont pas encore modélisées.
- Une validation imbriquée par lot, laboratoire, site et année est nécessaire avant toute comparaison de modèles complexe.

### Données et traçabilité

- Une transcription manuelle de tableau peut contenir une erreur ; un double contrôle et une empreinte du fichier source sont nécessaires.
- Les valeurs numérisées depuis une figure doivent conserver l’erreur de numérisation et l’image/page d’origine.
- Les unités, la géométrie, l’orientation, la vitesse d’essai et le conditionnement doivent être obligatoires.
- Une publication en accès libre et relue par les pairs n’implique pas que ses données soient compatibles avec la question posée.

## Plan expérimental recommandé

Pour le premier modèle PP réellement validable :

- au moins trois lots du grade cible ;
- au moins sept éprouvettes par lot et par temps ;
- temps 0, 7, 15, 30, 60, 90, 120, 180 et 365 jours ;
- une exposition naturelle et au moins trois températures accélérées ;
- mêmes géométrie, orientation, conditionnement et protocole de traction ;
- historique horaire de température, humidité, irradiance UV, pluie et cycles thermiques ;
- valeurs brutes par éprouvette, y compris exclusions et causes ;
- module, résistance à la traction, allongement à rupture, indice carbonyle, cristallinité et masse ;
- un lot complet et, si possible, un site ou une année complète réservés à la validation finale.

Le modèle et les critères de succès doivent être gelés avant d’ouvrir le jeu final. Les séparations de validation recommandées sont « lot laissé de côté », « site laissé de côté » et « année laissée de côté ».

## Cibles de performance proposées

Ces valeurs sont des objectifs de projet à discuter avec l’enseignant et le métier ; elles ne sont pas des normes :

- MAPE ≤ 5 % dans le domaine mesuré et sur la campagne externe ;
- biais moyen absolu ≤ 2 % de la propriété initiale ;
- couverture réelle d’un intervalle annoncé à 80 % comprise entre 75 et 85 % ;
- couverture réelle d’un intervalle annoncé à 90 % comprise entre 85 et 95 % ;
- erreur médiane sur le temps de franchissement ≤ 10 à 15 % lorsque le seuil est effectivement observé ;
- aucune durée annoncée au-delà de trois fois la fenêtre expérimentale sans nouvelle campagne ;
- aucune qualification si le grade, le protocole ou le mécanisme sortent du domaine déclaré.

## Audit logiciel et exploitation

| Domaine | État actuel | Suite requise pour une école |
|---|---|---|
| Reproductibilité | Manifeste, version et empreinte dans les résultats | Versionner aussi chaque jeu de données et chaque décision de revue |
| Tests | Suite automatisée des calculs, imports, droits et exports | Ajouter tests navigateur, accessibilité et non-régression visuelle |
| Comptes | Comptes locaux et rôles | SSO institutionnel, récupération de compte et journal d’administration |
| Stockage | SQLite et fichiers locaux | PostgreSQL, stockage objet, sauvegarde externalisée et restauration testée |
| Sécurité | Serveur local, secrets de revue séparés | HTTPS, reverse proxy, politiques de session, analyse de dépendances et audit de sécurité |
| Charge | Pilote local à 30 parcours simultanés | Test réaliste avec exports, imports, cours et volume documentaire |
| Disponibilité | Sonde de santé | Supervision, alertes, métriques, journal central et plan de reprise |

## Améliorations UX prioritaires

### À faire avant un pilote de classe

1. Ajouter un assistant de préparation des données qui affiche clairement ce qui manque avant de calculer.
2. Demander l’objectif au départ : lire une publication, comparer des formulations, préparer un essai ou estimer après 30 jours.
3. Afficher un badge permanent « observé », « interpolé » ou « extrapolé » à côté de chaque valeur et dans les exports.
4. Ajouter une fiche de correspondance entre le matériau choisi et la preuve : grade, additifs, procédé, géométrie, climat et protocole.
5. Montrer deux bandes activables : zone centrale interquartile et enveloppe complète min–max, avec une définition au survol.
6. Empêcher la comparaison directe de scénarios incompatibles ou afficher les différences avant de tracer.
7. Proposer des exemples guidés par niveau avec réponse attendue, erreurs fréquentes et barème enseignant.
8. Produire une « carte de preuve » d’une page, exportable, résumant source, domaine, hypothèses et limites.

### Ensuite

- import assisté des historiques météo et visualisation des doses cumulées ;
- planificateur d’expérience indiquant quels nouveaux temps réduisent le plus l’incertitude ;
- vue par lot et par éprouvette, avec détection documentée des valeurs atypiques ;
- comparaison multi-propriétés et critères de fin de vie adaptés à l’usage ;
- filtres par famille, grade, charge, procédé, propriété, exposition et niveau de preuve ;
- journal pédagogique expliquant comment chaque paramètre modifie le calcul ;
- navigation clavier complète, test WCAG 2.2 AA, contrastes, lecteurs d’écran et affichage mobile ;
- tableau de bord enseignant sur l’avancement, les erreurs de méthode et la qualité des sources, sans classement trompeur des étudiants ;
- recherche documentaire avec extraction semi-automatique, mais validation humaine obligatoire avant intégration au corpus.

## Feuille de route

### Étape 1 — fiabiliser le court terme

Collecter une campagne PP compatible jusqu’à 120 jours, intégrer les valeurs brutes, geler le modèle deux phases et tester sur le lot réservé. C’est la condition préalable à une bande prédictive calibrée.

### Étape 2 — apprendre l’environnement

Ajouter plusieurs températures et historiques climatiques, comparer Arrhenius, dose cumulée et modèles semi-paramétriques, puis vérifier la stabilité du mécanisme. Les revues de durée de vie des polymères rappellent que l’extrapolation d’Arrhenius exige plusieurs temps et conditions et peut échouer si le mécanisme change.

### Étape 3 — prévoir la fin de fonction

Définir un critère multi-propriétés lié à l’usage, traiter le temps de franchissement comme une variable potentiellement censurée, puis calibrer des intervalles sur des campagnes externes.

### Étape 4 — déployer à l’école

Mettre en place SSO, base serveur, stockage documentaire, sauvegardes hors site, supervision, audit de sécurité, tests d’accessibilité et procédure de revue scientifique à deux personnes.

## Références méthodologiques

- Matos et al., données PP utilisées par Materia : https://doi.org/10.3390/polym16131788
- NIST, modèles bayésiens hiérarchiques pour la durée de service des polymères : https://www.nist.gov/publications/bayesian-hierarchical-models-service-life-prediction-polymers
- NIST, outils de mesure pour le vieillissement accéléré : https://www.nist.gov/programs-projects/measurement-science-tools-accelerated-weathering-polymers-project
- Revue sur la prédiction de durée de vie des polymères : https://pmc.ncbi.nlm.nih.gov/articles/PMC7599543/
- Revue sur la corrélation vieillissement accéléré/naturel : https://pmc.ncbi.nlm.nih.gov/articles/PMC8398581/
- Conformalized Quantile Regression, calibration d’intervalles : https://doi.org/10.48550/arXiv.1905.03222
