# Architecture et décisions

## Chaîne exécutée

Navigateur → composants NiceGUI écrits en Python → validation Pydantic → calcul scientifique → graphique Plotly et export → enregistrement SQLite.

- `main.py` : pages et gestion des événements ; données propres à chaque page/session.
- `materia/science.py` : moteur synthétique, normalisation CSV, calibration.
- `materia/charts.py` : graphiques, axes et conventions.
- `materia/store.py` : persistance et filtrage obligatoire par propriétaire.
- `materia/literature.py` : accès asynchrone aux métadonnées Crossref.
- `materia/material_db.py` : registre réel sourcé, sources, état de maturité et table réservée aux observations expérimentales revues.
- `materia/experiments.py` : import CSV/XLSX, modèle de campagne et contrôle de qualité avant revue.
- `materia/validation.py` : test temporel PP, diagnostic d'applicabilité et budget d'incertitude.
- `materia/excel_reporting.py` et `materia/pdf_reporting.py` : rapports complets avec courbe, origine, validité et empreinte.
- `materia/classroom.py` : cours, travaux, remises, corrections, statistiques et duplication.
- `materia/maintenance.py` et `materia/deployment.py` : archives vérifiées, sauvegarde quotidienne, diagnostic de préparation et sonde de charge locale.
- API locale : `/api/materials` pour le catalogue et `/api/materials/{id}` pour une fiche, son domaine et ses observations acceptées.
- `materia/style.css` : présentation et réduction des animations.

## Choix d'interface

NiceGUI retenu pour gérer les sept espaces, composants accessibles, transitions discrètes et graphiques interactifs depuis Python, sans frontend JavaScript personnalisé. La preuve de concept comprend le parcours complet matériau → environnement → objectif → vérification → résultats. Streamlit aurait permis le calcul mais donne moins de contrôle sur la composition et les interactions de cette interface.

Les composants navigateur de NiceGUI utilisent Vue/Quasar ; ce sont des dépendances, pas un second code applicatif développé. Les styles CSS restent séparés du code scientifique.

## Persistance v5

SQLite en mode WAL est suffisant pour le pilote local mono-serveur. La table `records` conserve les documents JSON avec id, owner, kind, name, payload et created ; les tables spécialisées gèrent comptes, cours, corpus, revue et preuves. Le schéma courant est la version 5. PostgreSQL, un stockage objet et de vraies migrations restent requis avant un déploiement multi-serveur.

## Sécurité et exploitation

Écoute 127.0.0.1 ; cookie de session signé ; identifiant propriétaire décidé côté serveur. Aucun rôle administrateur sélectionnable par l'étudiant. Aucune API ne publie de modèle validé. Les imports sont limités en taille et normalisés, et les textes sont rendus par composants textuels. Aucune exécution des documents.

Crossref est le seul appel externe du produit et reçoit les mots-clés explicitement recherchés. Aucune donnée de laboratoire n'est envoyée à un service IA.

## Modèle

Trois lois exponentielles synthétiques, dont une croissante. La loi thermique est illustrative. E0 est une entrée positive, le seuil est relatif à E0 ; cela implique que le temps de seuil relatif du modèle simple ne dépend pas d'E0. Ce comportement est explicite et ne signifie pas que les matériaux réels ont cette propriété.

Les 1 000 trajectoires de sensibilité utilisent une graine fixée et une dispersion logarithmique réglable. Les franchissements hors horizon sont conservés dans la population, avec borne affichée hors horizon. Aucune probabilité de défaillance réelle n'est annoncée.

## Suite nécessaire

1. Acquérir une campagne PP indépendante sur le grade, le procédé et l'environnement cibles.
2. Réserver les lots et temps de validation avant de choisir le modèle final.
3. Calibrer un intervalle prédictif et vérifier les temps de franchissement de seuil.
4. Connecter l'identité institutionnelle, PostgreSQL, le stockage objet, HTTPS et la supervision.
5. Mener une réception avec enseignants et étudiants sur le réseau de l'école.

## Catalogue matériaux v0.3

Le catalogue initialise sept entrées documentaires : PE, LDPE, PET, époxy, PP, PA66 et PLA. PE/LDPE, PET et époxy sont prioritaires car le NIST décrit des travaux de validation sur ces familles. Les autres entrées préparent la taxonomie sans prétendre disposer de séries de vieillissement.

Les tables `materials`, `material_sources` et `material_observations` séparent l'identité, la provenance et les mesures. Une observation ne devient utilisable que si `review_status = accepted`. Le catalogue initial contient zéro observation acceptée et le contrôle de domaine refuse donc toute prédiction réelle. PoLyInfo est cité comme répertoire à consulter manuellement ; aucun scraping ni téléchargement massif n'est effectué.

Sites n'est pas utilisé comme hébergement : le serveur Python persistant de NiceGUI nécessite un hébergement adapté. Aucun déploiement public n'a été effectué.

## Extension documentaire v0.2

`documents.py` extrait les PDF texte dans un processus séparé limité à 30 secondes (limite CPU Unix de 20 secondes), 8 Mo, 100 pages et 1 million de caractères extraits. Ces limites ne constituent pas un bac à sable de production pour fichiers hostiles. Les originaux sont stockés dans SQLite avec leur empreinte SHA-256, les pages extraites et la référence déclarée. Les documents et preuves utilisent le même filtrage par propriétaire que les simulations.

`document_ui.py` ajoute une bibliothèque, une recherche de passages et des notes sourcées. La recherche compte les termes communs dans des fenêtres de texte ; aucun score probabiliste ni résumé génératif n'est annoncé. Les extraits sont vérifiés contre la source enregistrée lors de leur conservation. Une note personnelle n'accorde aucun statut de validation scientifique.

Les PDF scannés restent importables mais les pages sans texte sont explicitement signalées. Le numéro de page extrait est l'ordre physique dans le PDF, qui peut différer de la pagination imprimée. Les passages collés comportent une page déclarée par l'utilisateur.
