# Audit de Materia pour un usage en école d’ingénieurs

**Date :** 28 septembre 2026  
**Périmètre :** application `materia` uniquement  
**Objectif :** évaluer l’aptitude de Materia à être utilisé par une classe d’étudiants, puis définir les améliorations nécessaires pour obtenir un outil fiable, compréhensible, administrable et scientifiquement défendable.

## Conclusion

Materia est aujourd’hui un **prototype pédagogique individuel fonctionnel**. Les pages principales répondent, les 46 tests automatisés réussissent, la base contient 50 fiches matériaux et le parcours permet déjà d’explorer des scénarios de vieillissement.

Materia n’est toutefois **pas encore prêt pour un déploiement partagé à l’échelle d’une classe**. Les blocages principaux sont :

1. l’absence d’authentification institutionnelle et de rôles étudiant/enseignant/administrateur ;
2. la possibilité pour tout utilisateur de valider ou rejeter des données scientifiques globales ;
3. l’emploi de lois génériques pour de nombreux matériaux sans données de vieillissement propres ;
4. un stockage local qui ne convient pas encore à plusieurs dizaines d’utilisateurs et de documents ;
5. l’absence d’outils de cours, de devoirs, de groupes, de remise et de suivi enseignant ;
6. l’absence de tests complets avec 30 connexions interactives simultanées.

L’application peut être utilisée dès maintenant pour une démonstration encadrée ou un TP sur un poste individuel. Elle ne doit pas encore présenter ses projections comme des durées de vie validées pour tous les polymères.

## Niveau de maturité observé

| Domaine | Note | État actuel |
|---|---:|---|
| Fonctionnement du prototype | 7/10 | Navigation et fonctions principales opérationnelles |
| Expérience étudiante | 6/10 | Interface claire, mais page de simulation trop dense |
| Valeur pédagogique | 5/10 | Contenu explicatif présent, fonctions de classe absentes |
| Fiabilité scientifique | 3/10 | Une calibration limitée au PP extérieur ; extrapolations importantes |
| Données et traçabilité | 5/10 | Sources visibles, mais corpus validé encore trop faible |
| Sécurité et gestion des rôles | 2/10 | Identité locale, aucun rôle institutionnel |
| Usage simultané en classe | 3/10 | Aucun test réaliste des sessions interactives NiceGUI |
| Accessibilité | 5/10 | Bon socle visuel, graphiques encore peu accessibles |
| Exploitation et maintenance | 3/10 | Pas de déploiement, supervision et restauration industrialisés |
| Maintenabilité du code | 5/10 | Tests utiles, mais fichier principal monolithique |

## Résultats vérifiés

### Application

- Les routes principales `/`, `/materiaux`, `/simuler`, `/comparer`, `/projets`, `/comprendre`, `/documents`, `/donnees`, `/health` et `/api/materials` répondent correctement.
- Les **46 tests automatisés** réussissent.
- Le contrôle de santé indique la version `0.11.0` et signale correctement que la validation scientifique globale n’est pas acquise.
- Les temps de réponse séquentiels sont bons sur la machine locale.
- Une charge HTTP synthétique de 150 requêtes n’a provoqué aucune erreur, mais le 95e percentile a dépassé 10 secondes. Ce test ne couvre pas les connexions WebSocket interactives utilisées par NiceGUI.

### Base de données

- 50 fiches matériaux sont présentes.
- 8 sources, 12 valeurs MDPI vérifiées et 10 observations hygrothermiques acceptées sont enregistrées.
- Les 10 observations Scida sont acceptées pour l’interpolation descriptive dans leur domaine exact. Deux expériences restent insuffisantes pour entraîner ou valider un modèle prédictif.
- L’intégrité SQLite est correcte et le journal WAL est activé.
- Les clés étrangères ne sont pas activées à chaque connexion.
- Les recherches par propriétaire et type d’enregistrement ne disposent pas d’index dédié.
- Les PDF sont conservés en Base64 dans des enregistrements JSON. Ce choix augmentera fortement la taille de la base et la mémoire consommée avec une classe entière.

### Modèle scientifique

- Le modèle calcule correctement ses courbes selon les formules actuellement implémentées.
- Les profils non calibrés utilisent des demi-vies génériques par famille, puis des facteurs de température, humidité, environnement et épaisseur.
- Le module de Young initial d’une fiche technique décrit l’état de départ ; il ne suffit pas à déterminer une cinétique de vieillissement.
- La seule plage d’incertitude réellement resserrée à partir des données intégrées concerne le PP exposé en extérieur.
- Cette calibration repose sur quatre formulations de PP recyclé observées jusqu’à 120 jours. Une projection sur plusieurs années reste donc une extrapolation importante.
- Pour les autres familles, la plage d’incertitude est une enveloppe d’ingénierie et ne constitue pas un intervalle statistique validé.

## Corrections indispensables avant un usage collectif

### P0 — Bloquants

#### 1. Authentification et rôles

Ajouter une connexion institutionnelle, idéalement par OIDC ou SAML, puis définir au minimum :

- **Étudiant :** consulter les ressources autorisées, lancer ses simulations, gérer ses projets et remettre un travail ;
- **Enseignant :** créer un cours, publier des jeux de données, consulter les remises et commenter les résultats ;
- **Validateur scientifique :** accepter ou rejeter les observations avec une identité certifiée ;
- **Administrateur :** gérer les utilisateurs, les quotas, les sauvegardes et les versions scientifiques.

La validation scientifique globale doit être inaccessible aux étudiants. Chaque décision doit produire une entrée d’audit immuable avec auteur, date, version de la donnée et justification.

#### 2. Distinguer clairement estimation et prédiction validée

Chaque résultat doit afficher l’un des niveaux suivants :

- **Démonstration pédagogique** : données synthétiques ;
- **Estimation exploratoire** : hypothèses génériques, sans validation propre au matériau ;
- **Modèle calibré** : calibration documentée pour un matériau et un domaine précis ;
- **Prédiction validée** : performance évaluée sur des données indépendantes.

Une fiche technique seule doit conduire à un **scénario de présélection**, jamais à une promesse de durée de vie. Pour un matériau hors domaine de validité, l’application doit refuser la prédiction validée et expliquer les données manquantes.

#### 3. Domaine de validité scientifique

Commencer par deux ou trois cas solides plutôt que de prétendre prédire les 50 matériaux :

1. sélectionner un polymère, un mécanisme et une propriété, par exemple PP extérieur et module de Young ;
2. intégrer plusieurs études indépendantes, avec formulation, géométrie, protocole, température, humidité, UV et durée ;
3. réserver une partie des données pour la validation ;
4. comparer le modèle à des références simples ;
5. mesurer les erreurs et calibrer les intervalles de prédiction ;
6. publier une fiche de modèle avec limites d’emploi.

L’incertitude doit provenir des données, de la dispersion inter-études et de l’erreur hors échantillon. Elle ne doit pas être resserrée uniquement pour améliorer l’apparence de la courbe.

#### 4. Architecture multi-utilisateur

Pour un serveur d’école, migrer vers :

- PostgreSQL pour les utilisateurs, cours, projets, données et historiques ;
- un stockage de fichiers séparé pour les PDF et exports ;
- une file de tâches pour les extractions PDF, entraînements et calculs longs ;
- HTTPS derrière un proxy ;
- des quotas par utilisateur et par cours ;
- des sauvegardes planifiées avec essais de restauration.

SQLite peut rester disponible pour une édition locale monoposte.

#### 5. Mise sous contrôle du code

Le dossier `materia` apparaît actuellement comme non suivi dans le dépôt Git parent. Il faut l’ajouter à un dépôt versionné, créer une branche principale protégée, automatiser les tests et conserver chaque version livrée. Cette étape est indispensable pour revenir en arrière, comparer les modifications et garantir la reproductibilité des séances.

## Améliorations fonctionnelles prioritaires

### P1 — Version classe

#### Espaces pédagogiques

Ajouter :

- des promotions, cours et groupes ;
- des invitations ou une synchronisation avec l’annuaire de l’école ;
- des scénarios de TP préparés par l’enseignant ;
- des dates de remise, états brouillon/remis/corrigé et commentaires ;
- un tableau de bord enseignant montrant progression, erreurs fréquentes et remises ;
- un export des résultats et notes en CSV ;
- des modèles de projet duplicables pour chaque étudiant ou groupe.

#### Parcours étudiant

La page `/simuler` réunit actuellement trois usages différents et devient longue. La remplacer par un choix initial :

1. **Explorer une fiche matériau** ;
2. **Analyser des mesures expérimentales** ;
3. **Apprendre avec un exercice guidé**.

Chaque parcours doit comporter peu d’étapes, une barre de progression, des valeurs d’exemple, un bouton de réinitialisation et une explication immédiate du résultat.

Prévoir deux niveaux d’affichage :

- **Mode apprentissage**, guidé et illustré ;
- **Mode recherche**, avec paramètres avancés, diagnostics et export complet.

#### Rapport reproductible

Toute simulation exportée doit contenir :

- les paramètres et unités ;
- l’identifiant et la version du matériau ;
- les sources et données utilisées ;
- la version du modèle et du logiciel ;
- le domaine de validité ;
- les indicateurs d’erreur et l’incertitude ;
- les avertissements et hypothèses ;
- la date, l’auteur et, le cas échéant, la graine aléatoire.

#### Accessibilité

Conserver les contrastes, le focus visible et la réduction des animations déjà présents, puis ajouter :

- une description textuelle de chaque graphique ;
- un tableau de données accessible sous chaque courbe ;
- une navigation complète au clavier ;
- des messages d’erreur associés aux champs ;
- des tests avec lecteur d’écran ;
- une vérification WCAG 2.2 AA sur tous les parcours essentiels ;
- des tests mobiles sur toutes les pages, pas seulement l’accueil.

### P1 — Qualité logicielle

- Découper `main.py` en pages, composants, services et politiques d’autorisation.
- Introduire de vraies migrations de base versionnées.
- Activer les clés étrangères SQLite à chaque connexion.
- Ajouter des index sur les colonnes recherchées, notamment propriétaire, type, statut et cours.
- Paginer les listes et ne plus charger tous les documents en mémoire.
- Ajouter un cache avec temporisation et reprise contrôlée pour les appels Crossref.
- Versionner les jeux de données et les modèles ; rendre chaque publication scientifique immuable.
- Centraliser les journaux applicatifs sans enregistrer les documents ou données personnelles sensibles.

## Évolutions scientifiques recommandées

### Structure des données

Chaque observation de vieillissement devrait enregistrer au minimum :

- polymère, grade, formulation, renfort, charge et additifs ;
- procédé, cristallinité, orientation, porosité et état initial ;
- géométrie de l’éprouvette et épaisseur ;
- milieu, température, humidité, oxygène, UV, dose et cycles ;
- norme et protocole d’essai ;
- propriété mesurée, unité, répétitions, moyenne et dispersion ;
- temps d’exposition et méthode de vieillissement accéléré ;
- DOI, page, figure ou tableau source ;
- méthode d’extraction, relecture humaine et niveau de confiance.

### Validation des modèles

Utiliser une séparation par étude ou par campagne expérimentale afin d’éviter qu’une même série soit présente dans l’apprentissage et le test. Publier au minimum MAE, RMSE, biais, coefficient de détermination lorsque pertinent, couverture des intervalles et erreur sur le temps de franchissement du seuil.

Comparer systématiquement :

- une loi physique simple ;
- une régression statistique ;
- un modèle plus complexe uniquement s’il améliore les résultats hors échantillon.

Les modèles d’apprentissage automatique, réseaux neuronaux ou PINN ne doivent être ajoutés qu’après constitution d’un corpus suffisamment grand et diversifié.

## Tests à ajouter

### Parcours complets

- connexion étudiant et enseignant ;
- création d’un cours et inscription d’une classe ;
- lancement, sauvegarde, reprise et remise d’une simulation ;
- correction par l’enseignant ;
- interdiction pour un étudiant de modifier une donnée globale ;
- export et réimport d’un projet ;
- expiration de session et récupération après interruption.

### Données et sécurité

- accès croisé entre deux étudiants ;
- validation scientifique réservée aux rôles autorisés ;
- téléversement de fichiers invalides ou volumineux ;
- concurrence d’écriture ;
- migration d’une ancienne base ;
- restauration d’une sauvegarde ;
- suppression et export des données personnelles.

### Charge

Tester 30 sessions interactives NiceGUI simultanées, avec navigation, sauvegardes, graphiques, exports et traitement de PDF. Mesurer le temps de réponse perçu, la mémoire, le processeur, les erreurs WebSocket et la reprise après redémarrage.

### Validation scientifique

Créer un jeu de référence figé dont les résultats attendus ont été vérifiés manuellement. Les tests doivent détecter toute variation des prédictions, unités, intervalles ou seuils lors d’une nouvelle version.

## Critères de recette pour déclarer Materia « prêt pour une classe »

- 30 étudiants et 2 enseignants utilisent simultanément l’application sans perte de session ou de données.
- Le 95e percentile des interactions courantes reste inférieur à 2 secondes ; les calculs longs affichent leur progression.
- Aucun étudiant ne peut lire ou modifier les travaux privés d’un autre étudiant.
- Aucun étudiant ne peut valider une observation scientifique globale.
- Une sauvegarde complète peut être restaurée sur un environnement vierge lors d’un exercice documenté.
- Chaque résultat indique clairement son niveau de preuve et son domaine de validité.
- Chaque rapport est reproductible à partir des versions de données et de modèles indiquées.
- Les parcours principaux satisfont les contrôles WCAG 2.2 AA retenus par l’établissement.
- Les tests automatisés, de migration, de sécurité et de parcours réussissent avant chaque livraison.
- Un pilote de 10 utilisateurs, puis un pilote de classe, sont réalisés avant la mise en production générale.

## Feuille de route proposée

### Phase 0 — Stabilisation, 1 à 2 semaines

- placer Materia sous contrôle de version ;
- séparer les trois parcours de simulation ;
- verrouiller la validation scientifique ;
- afficher partout le niveau de preuve ;
- ajouter migrations, clés étrangères et index ;
- corriger la documentation devenue incohérente avec les 46 tests actuels.

### Phase 1 — Socle classe, 3 à 5 semaines

- authentification et rôles ;
- cours, groupes, projets et remises ;
- PostgreSQL et stockage séparé des fichiers ;
- tableau de bord enseignant ;
- journal d’audit et politique de conservation ;
- environnement de préproduction, sauvegardes et supervision.

### Phase 2 — Pédagogie et accessibilité, 3 à 4 semaines

- exercices guidés et jeux de données exemples ;
- rapports reproductibles ;
- graphiques accessibles et navigation clavier ;
- tests de parcours, mobiles et d’accessibilité ;
- pilote avec 10 étudiants et collecte structurée des retours.

### Phase 3 — Validation scientifique, 4 à 8 semaines par domaine

- consolider un corpus sur deux ou trois domaines ciblés ;
- documenter les protocoles d’extraction et de revue ;
- entraîner et valider les modèles sur des études indépendantes ;
- calibrer les incertitudes ;
- publier les fiches de modèle et leurs limites.

### Phase 4 — Pilote de classe et mise en production

- test de charge avec 30 utilisateurs ;
- exercice de restauration ;
- revue de sécurité et de protection des données ;
- séance pilote en conditions réelles ;
- correction des problèmes observés avant ouverture générale.

## Ce qu’il vaut mieux différer

Pour la prochaine version, ajouter davantage de matériaux génériques, un chatbot ou des modèles neuronaux apporterait moins de valeur que la fiabilisation du socle. La priorité est de rendre les résultats traçables, de sécuriser les rôles et de valider un petit nombre de domaines scientifiques de bout en bout. Une fois ce socle acquis, l’extension à de nouvelles propriétés et familles de matériaux deviendra beaucoup plus sûre et plus rapide.
