# Rapport de validation du prototype — 30 septembre 2026

## Extension v0.39 du référentiel

Le catalogue contient désormais 75 matériaux. Vingt-et-un profils de module initial couvrent 19 matériaux et sont associés à deux supports fabricant officiels, avec le grade, la norme, le conditionnement, le procédé et la température d'essai. Cette validation documentaire concerne uniquement la propriété initiale. Elle ne transforme pas une fiche technique en série de vieillissement et ne relève pas le niveau de preuve de la cinétique.

## Situation actuelle - v0.20

- 77 tests automatisés couvrent les calculs, ancres temporelles PP, imports CSV/XLSX, compatibilité des anciens jeux, exports XLSX/PDF, comptes, droits, classe, sauvegardes et diagnostics de validité.
- Le corpus PP contient 12 valeurs publiées : quatre formulations, trois temps, sept éprouvettes par point et les écarts-types du tableau 2 de Matos et al. (2024).
- Un test interne laisse chaque formulation de côté, utilise ses valeurs à 0 et 30 jours et estime le ralentissement sur les trois autres formulations. À 120 jours, la MAE est de 3,83 MPa et la MAPE de 0,77 %. Il mesure un transfert interne à la même publication ; il ne constitue pas une validation indépendante.
- Martorell et al. (2022), DOI `10.3390/en15228340`, est conservé comme preuve externe contextuelle. Le film PP-35, l'épaisseur, le domaine d'usage et les directions d'essai sont incompatibles avec le PP H301 retransformé : cette source est donc exclue des scores numériques.
- Chaque résultat distingue la dispersion mesurée, la bande affichée, l'extrapolation temporelle et le transfert de formulation. Une composante non quantifiée est annoncée comme telle.
- Le PDF final a été rendu et inspecté sur ses deux pages. La sonde de charge locale et les routes HTTP sont documentées dans les rapports de livraison.

Le statut scientifique global reste **non validé**. Les résultats PP publiés autorisent une interpolation descriptive jusqu'à 120 jours pour la formulation exacte. Les projections issues d'une fiche matériau restent des estimations de présélection.

## Règle d'incertitude v0.16

Materia distingue la dispersion publiée (±1 écart-type, `n=7`) de l'IC95 % de la moyenne pour les données PP. Les points lin/époxy portent uniquement une erreur estimée de numérisation. Aucun de ces deux objets n'est qualifié d'intervalle de prédiction de durée de vie.

## Résultats logiciels

- 23 tests pytest réussis (dernière exécution : 0,61 s).
- Sept routes principales répondent HTTP 200.
- Calcul synthétique : environ 2,05 ms en moyenne sur 20 appels locaux ; ceci n'est ni un temps complet navigateur ni un test de charge.
- Parcours navigateur vérifié : saisie en cinq étapes → calcul → sauvegarde → présence dans Mes projets.
- Import CSV par collage vérifié : huit mesures synthétiques appartenant à deux expériences.
- Calibration affichée : E0 ≈ 2010 MPa et k ≈ 0,00105361 jour⁻¹ ; contrôle réservé SYNTH-B, erreur absolue moyenne ≈ 17,20 MPa. Ce résultat porte sur un jeu fabriqué, pas sur un matériau réel.
- Recherche Crossref vérifiée : huit références renvoyées avec titres et DOI.
- Comparaison de températures affichée : seuils illustratifs de 900, 319 et 127 jours à 40, 60 et 80 °C pour le cas A.
- Interface inspectée sur ordinateur et à 390 × 844 px. À 390 px, largeur du document = largeur du viewport : aucun débordement horizontal sur l'accueil. Menu mobile ouvert avec succès.
- Les contrôles d'import et la sauvegarde/restauration ont des tests automatisés.

## Limites des vérifications

Le parcours du sélecteur de fichiers natif n'a pas pu être vérifié jusqu'au bout via l'outil navigateur ; la chaîne d'import a été vérifiée par l'alternative de collage qui utilise le même parseur. Les téléchargements sont implémentés et leur contenu CSV est testé, mais leur réception sur disque n'a pas été vérifiée dans le navigateur.

Pas de réception par de vrais étudiants, pas d'audit WCAG complet, pas de test de 30 utilisateurs simultanés, pas de test de déploiement partagé.

## Validation scientifique

Aucune. Les tests prouvent des propriétés du calcul et du logiciel, pas l'adéquation des modèles aux polymères. Aucun matériau réel n'a été choisi à partir d'un audit documentaire achevé. Les références Crossref ne constituent pas un corpus expérimental validé.

## Conditions pour passer à un modèle réel

- Choisir une formulation et un mécanisme avec un référent matériaux.
- Rassembler des séries temporelles traçables et suffisamment comparables.
- Réserver des expériences indépendantes avant la sélection des modèles.
- Évaluer erreurs, surestimation des temps de seuil et intervalles.
- Vérifier le transfert accéléré–service sur des observations pertinentes.
- Définir le domaine autorisé et les refus.

La séparation des capacités implémentées et non validées est également visible dans Données et modèles → Modèles et maturité.

## Extension documentaire — même journée

31 tests automatisés réussis après ajout de la bibliothèque. Nouveaux contrôles : extraction PDF en processus séparé, PDF invalide/surdimensionné/chiffré, page vide, déduplication par empreinte dans une session, isolation des documents, recherche insensible aux accents, fidélité des citations et refus des preuves d'un autre propriétaire.

Parcours navigateur vérifié : ajout d'un passage synthétique avec page 3 → recherche « module température » → affichage du passage exact avec page → ajout d'une note → présence dans Mes preuves et notes. Le sélecteur PDF natif n'a pas été testé de bout en bout ; le moteur d'extraction et l'enregistrement PDF sont testés automatiquement.

Cette extension est une extraction textuelle et une recherche par mots-clés. Elle n'est ni un OCR, ni une extraction IA de mesures, ni une validation scientifique.

## Catalogue matériaux v0.3

Sept familles réelles et quatre sources ont été ajoutées au registre. Les sources incluent NIMS PoLyInfo, sa définition du module en traction, la page NIST consacrée au vieillissement accéléré et une publication candidate sur le LDPE. Aucun accès automatisé aux valeurs PoLyInfo n'est effectué, conformément à l'interdiction de téléchargement massif annoncée par le service.

Le garde-fou est testé : toutes les fiches réelles ont zéro observation acceptée et `can_predict = false`. Le catalogue sert donc à organiser la collecte, pas à produire artificiellement une durée de vie.

Un jeu CSV peut désormais être rattaché à un matériau et à une URL de provenance. Les lignes entrent uniquement avec le statut `pending`, les doublons source/expérience/temps sont ignorés, et une donnée en attente ne débloque jamais la prédiction.

## Pipeline hygrothermique et Machine Learning v0.4

Le schéma obligatoire reprend les quatre variables du sujet : température, humidité relative, temps d’exposition en heures et épaisseur. La cible `E/E₀` est calculée à partir des modules normalisés en MPa. La comparaison évalue Ridge, Random Forest et un algorithme de boosting avec des plis séparés par expérience. Elle publie R², RMSE, MAE, écart apprentissage-validation et importance des variables.

Le jeu synthétique livré contient 12 points et 3 expériences. Il vérifie le fonctionnement du pipeline mais ne valide aucun polymère. Sur ce Mac, XGBoost Python est installé mais son moteur natif attend OpenMP ; le logiciel le signale et utilise temporairement `HistGradientBoostingRegressor`. Les 38 tests automatisés réussissent.

## Revue scientifique v0.5

Les lots proposés sont regroupés par source et expérience. Une acceptation exige quatre confirmations explicites : source consultée, conditions vérifiées, unités vérifiées et extraction comparée à la source. Le relecteur et sa justification sont horodatés. Un lot incomplet ou comportant moins de trois temps ne peut pas être accepté. Le seuil technique de modélisation est fixé à 12 observations acceptées sur 3 expériences ; il ouvre une évaluation interne, jamais le statut « validé ». Les 39 tests automatisés réussissent.

## Premier corpus candidat réel v0.6

Scida et al., DOI `10.1016/j.compositesb.2012.12.010`, fournit le module de Young d’un stratifié lin/époxy de 2,5 mm exposé à 90 % HR à 20 et 40 °C. Dix points correspondant à 0, 1, 3, 9 et 38 jours ont été numérisés depuis la figure 4a. Le module initial de 26,6 GPa et les valeurs finales de 12,0 et 11,2 GPa sont confirmés dans le texte ; les valeurs intermédiaires conservent la méthode `figure_digitization` et une incertitude de lecture estimée à ±3 %. Les deux expériences restent `pending`. Elles sont insuffisantes pour la validation croisée minimale de trois expériences et ne peuvent produire aucune prédiction réelle. Les 40 tests automatisés réussissent.

## Catalogue étendu et bêta utilisable v0.7

Le catalogue contient 40 matériaux répartis entre polymères courants, techniques et haute performance, fluoropolymères, thermodurcissables, élastomères, biopolymères et composites. Les nouvelles entrées sont des fiches taxonomiques reliées à NIMS PoLyInfo ; elles ne contiennent aucune courbe inventée. L’interface permet la recherche, le filtrage par famille et maturité, l’export CSV du catalogue, l’inspection et l’export JSON de chaque lot expérimental. Une API locale en lecture seule expose `/api/materials` et `/api/materials/{id}`.

## Taxonomie contrôlée v0.8

Le catalogue atteint 50 matériaux. Chaque fiche comporte désormais une grande classe, une sous-catégorie, une famille, un sous-type et un statut de preuve. La taxonomie structurale est reliée aux définitions NIMS PoLyInfo et la terminologie générale à l’IUPAC Gold Book. Le statut `taxonomy_verified` certifie uniquement l’identité et le classement documentaire ; il ne certifie aucune propriété ni durée de vie. Le statut `experimental_pending` désigne les observations encore soumises à revue. Seul `accepted` autorise une observation dans un entraînement réel.

## Simulateur relié au catalogue v0.9

Le simulateur peut sélectionner les 50 fiches du catalogue. Une courbe n'est produite que lorsqu'au moins trois observations existent pour la combinaison exacte matériau–température–humidité–épaisseur. Le calcul est une interpolation linéaire des points publiés, jamais une prédiction hors domaine, et l'horizon est limité au dernier temps observé. Le graphique conserve les points sources et une enveloppe issue de l'incertitude d'extraction déclarée.

Les dix points lin/époxy ont d’abord été conservés en attente. Le 29 septembre 2026, le PDF primaire, le protocole et la figure 4a ont été relus. Ils sont désormais acceptés pour une interpolation descriptive limitée à 0–38 jours, aux conditions exactes de 20 ou 40 °C, 90 % HR et 2,5 mm. Deux expériences et dix points ne satisfont pas le seuil de 12 points et trois expériences : l’entraînement reste bloqué et aucune extrapolation de durée de vie n’est autorisée.

L’article indique que les essais de traction ont été réalisés à température ambiante sans valeur numérique. L’ancienne valeur nominale de 23 °C a donc été supprimée de la base. Le protocole conserve ASTM D3039, 2 mm/min, un extensomètre de 50 mm et cinq éprouvettes.

## Estimateur depuis une fiche standard v0.10

Les 50 matériaux peuvent désormais produire une courbe de présélection à partir d'un module initial fourni par une fiche technique. Le calcul combine une demi-vie générique par famille, une accélération thermique de type Q10 et des facteurs explicites d'humidité, de milieu et d'épaisseur. Il affiche le franchissement du seuil et une plage prudente obtenue en divisant et multipliant la vitesse centrale par trois. Il s'agit d'une estimation d'ingénierie, distincte des observations publiées et d'une prédiction validée pour un grade. Les 42 tests automatisés réussissent.

## Recalibrage MDPI v0.11

Le tableau 2 de l’article MDPI *Natural Aging of Reprocessed Polypropylene Composites Filled with Sustainable Corn Fibers* (DOI `10.3390/polym16131788`) a été transcrit dans une table de preuves séparée. Le corpus comprend quatre formulations, trois temps (0, 30 et 120 jours), soit 12 moyennes de module de Young avec leur écart-type et `n=7`. Les conditions météo n’étant pas résumées par une température et une humidité constantes, ces preuves ne sont pas injectées artificiellement dans la table hygrothermique.

Pour le PP en exposition extérieure, les quatre vitesses observées remplacent la plage générique ×/÷3 : la médiane produit la courbe centrale et les vitesses minimale et maximale encadrent la plage inter-formulations. Pour les autres matériaux ou milieux, la plage générique demeure tant qu’un corpus comparable n’est pas disponible. Cette réduction est donc fondée sur des données, mais son extrapolation au-delà de 120 jours reste une hypothèse à vérifier.
