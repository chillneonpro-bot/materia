# Materia

**Python 3.11–3.13 · Windows · macOS · Linux · Docker**

Version actuelle : **0.39.0**. Materia est prêt à être distribué dans un dépôt GitHub : lancement assisté sur macOS et Windows, image Docker, données persistantes et tests automatiques sur les trois systèmes. Voir le [guide utilisateur illustré en PDF](docs/Guide_utilisateur_Materia_v0.38.pdf), sa [version Word modifiable](docs/Guide_utilisateur_Materia_v0.38.docx), [l'installation complète](docs/INSTALLATION.md), [la mise à jour v0.39](docs/MISE_A_JOUR_V0.39.md) et [la distribution v0.38](docs/MISE_A_JOUR_V0.38.md).

Application Python de découverte et d'exploration du vieillissement des polymères. Interface NiceGUI, graphiques Plotly, calcul NumPy/SciPy et persistance SQLite.

**État : version locale fonctionnelle pour l’exploration et un pilote de classe, sans modèle de durée de vie scientifiquement validé.** Materia distingue les projections exploratoires, les mesures publiées et les exercices synthétiques. Chaque résultat affiche son niveau de preuve, son domaine de validité et les usages interdits.

## Ouvrir Materia

### Sur l'ordinateur de chaque étudiant

1. Téléchargez le ZIP du dépôt GitHub et décompressez-le.
2. Installez [Python 3.13](https://www.python.org/downloads/) si nécessaire.
3. **macOS :** double-cliquez sur `Lancer-Materia.command`.
4. **Windows :** double-cliquez sur `Lancer-Materia-Windows.bat`.

Le premier lancement crée un environnement isolé et installe automatiquement les composants. Le navigateur s'ouvre ensuite sur [http://127.0.0.1:8087](http://127.0.0.1:8087). Les lancements suivants sont directs tant que les dépendances ne changent pas.

Avec Docker :

```sh
docker compose up --build
```

### Avec une URL commune pour toute la classe

Déployez une seule instance Docker sur un serveur : les étudiants n'installent alors ni Python ni Docker et utilisent Materia depuis leur navigateur, sur macOS, Windows, Linux, tablette ou Chromebook. La base et les comptes sont conservés dans le volume persistant du serveur.

GitHub Pages ne peut pas exécuter cette application Python. Pour obtenir cette URL commune, déployez l'image Docker derrière HTTPS et définissez les deux codes d'administration dans `.env`. Les instructions et les variables sont détaillées dans [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Parcours disponibles

- Accueil : aperçu pédagogique et accès aux fonctions.
- Matériaux : recherche dans un catalogue réel de 75 polymères et composites.
- Catalogue réel : 21 profils de module initial pour 19 matériaux sont recoupés entre deux documents fabricant officiels. Grade, norme, conditionnement, procédé et plage restent visibles.
- Simuler : page d’orientation vers deux parcours : fiche matériau et mesures publiées.
- Fiche matériau : estimation centrale sur les 75 fiches à partir du module initial, de la température, de l'humidité, de l'épaisseur et du milieu. Un module fabricant recoupé est proposé lorsqu’il existe ; la cinétique reste explicitement séparée. Le rapport affiche le niveau de preuve, les facteurs, les limites, une table accessible et une empreinte reproductible.
- Mesures publiées : quatre formulations PP issues du tableau MDPI sont tracées avec leur écart-type. L’interpolation reste limitée à 0–120 jours et l’extrapolation est bloquée.
- Preuves MDPI : 12 valeurs exactes de module du PP, issues de quatre formulations suivies à 0, 30 et 120 jours, recalibrent la courbe extérieure et sa plage inter-formulations.
- Comparer : un à quatre matériaux ou simulations enregistrées ; axes communs.
- Mes projets : retrouver les résultats avec la version conservée, exporter un classeur Excel illustré ou un rapport étudiant lisible, archiver ou supprimer les projets.
- Mon compte : compte local étudiant ou enseignant, mot de passe haché, conservation des projets entre navigateurs et droits adaptés au profil.
- Espace classe : création de cours réservée aux enseignants, code d’accès, travaux, consignes, parcours demandé, remise d’une simulation, correction, note sur 20, retour étudiant et export Excel des notes.
- Comprendre : six fiches et un exercice interactif.
- Données et modèles : import CSV hygrothermique contrôlé, calcul de `E/E₀`, rattachement à un matériau et une URL source, revue scientifique traçable, entraînement limité au corpus accepté, comparaison Ridge/Random Forest/boosting par expérience, interprétabilité et recherche Crossref.
- Mes documents : import de PDF texte, lecture par page, recherche locale et notes avec références. PDF limités à 8 Mo et 100 pages. Les scans nécessitent un OCR externe ou une transcription ; aucun texte n’est inventé. Les nouveaux originaux sont stockés séparément de SQLite et protégés par session ; les anciens documents Base64 sont migrés automatiquement à l’ouverture de la bibliothèque.

## Premiers essais

1. Dans Simuler, ouvrir **Mesures publiées** et comparer les quatre formulations PP à 120 jours.
2. Vérifier que la fenêtre publiée et la zone extrapolée sont clairement séparées lorsque l’horizon dépasse 120 jours.
3. Ouvrir **Fiche matériau**, choisir un matériau et lire le niveau de preuve avant la courbe.
4. Déplier la méthode et vérifier les facteurs, avertissements et l’empreinte du calcul.
5. Comparer deux matériaux à conditions communes et exporter le classeur Excel.
6. Créer un compte, enregistrer le résultat, puis rejoindre un cours dans **Espace classe**.

## Tests

```sh
.venv/bin/python -m pytest -q
```

Les tests couvrent aussi l'interpolation des observations, le refus d'extrapoler au-delà du dernier temps mesuré, les comptes locaux, les droits enseignants, la protection de la revue scientifique et le cycle cours–travail–remise. Ils ne prouvent pas la validité sur des polymères réels.

## Données et comptes

Les données sont dans `data/materia.sqlite3`. Les visiteurs peuvent essayer le logiciel dans une session invitée. Lors de la création d’un compte ou de la première connexion, les projets de cette session sont rattachés au compte. Les mots de passe sont salés et dérivés avec scrypt ; ils ne sont jamais conservés en clair.

Les comptes enseignants nécessitent un code serveur. Au premier lancement local, Materia génère ce code dans `data/.teacher_token` avec des droits de lecture restreints. `MATERIA_TEACHER_TOKEN` permet de fournir un secret géré par l’établissement et reste prioritaire. Cette identité locale rend le pilote de classe utilisable ; un déploiement à l’échelle de l’école doit la remplacer ou la relier au SSO.

Le secret local est généré au premier lancement dans `data/.secret`. Les sessions NiceGUI sont dans `.nicegui/`. Ces fichiers sont ignorés par Git. Pour une publication Internet, utiliser le déploiement Docker documenté, des codes d'administration longs, un volume persistant et un domaine HTTPS.

La file de validation scientifique est verrouillée par défaut. Son code local est généré dans `data/.review_token` ; `MATERIA_REVIEW_TOKEN` permet de le remplacer. Il faut un compte enseignant ou administrateur et ce second code pour accepter ou rejeter une expérience.

## Sauvegarde vérifiable

Créer puis contrôler une archive comprenant la base et les PDF séparés :

```sh
.venv/bin/python -m materia.maintenance backup data/backups/materia.zip
.venv/bin/python -m materia.maintenance verify data/backups/materia.zip
```

Le manifeste conserve la version de schéma, la taille et l’empreinte SHA-256 de chaque fichier. La vérification contrôle aussi l’intégrité SQLite.

## Limites explicites

Pas encore implémentés : authentification institutionnelle, administration centralisée des comptes, réinitialisation de mot de passe, extraction IA/OCR des publications, assistant conversationnel, intervalle prédictif validé pour toutes les familles, historique environnemental variable et choix automatique d'expériences. Hors PP extérieur, le corpus reste trop petit pour calibrer une incertitude statistique par matériau. La courbe centrale générique est donc une estimation de présélection, explicitement séparée des modèles informés par plusieurs publications.

Les publications Crossref fournissent des références ; elles ne sont ni extraites ni validées automatiquement. Les mesures importées restent en attente de validation et ne modifient pas le catalogue.

Voir `docs/ARCHITECTURE.md`, `docs/DICTIONNAIRE.md`, `docs/VALIDATION.md` et `docs/EXPLOITATION.md` pour les détails et la suite du projet. Le cahier des charges original est conservé dans `docs/CAHIER_DES_CHARGES.txt`.
