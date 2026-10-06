# Materia v0.29 — audit complet du site

L’audit v0.29 couvre les 16 pages de l’application, les trois simulateurs visibles, le comparateur, la validation aveugle, les projets, les comptes, l’espace classe, les documents, les données scientifiques et les API locales.

## Corrections appliquées

- Les onglets de **Mes documents** et **Données et modèles** restent maintenant dans la largeur de l’écran sur téléphone et peuvent défiler horizontalement à l’intérieur du composant.
- Le tiroir de navigation possède un état initial explicite. Les changements rapides de page ne provoquent plus d’attente JavaScript ni de trace d’erreur serveur.
- Les nombres importants utilisent les conventions françaises : espace fine pour les milliers et virgule décimale. Une valeur comme 1 502 MPa ne peut plus apparaître sous la forme ambiguë `1,502 MPa`.
- Les tableaux affichent des intitulés français pour les scénarios, critères, résultats, métriques de Machine Learning et mesures de validation.
- Le tableau de l’exercice A/B/C utilise désormais l’en-tête **Scénario** au lieu de **Température** pour une ligne contenant à la fois le polymère et la température.
- Un horizon inférieur à un jour est réellement refusé, conformément au texte de l’interface.
- Un seuil de conservation fixé à 100 % est indiqué comme atteint **immédiatement**.
- Les dates limites de devoir sont validées au format `AAAA-MM-JJ` avant enregistrement.
- La suppression d’un matériau personnalisé demande une confirmation et précise que les simulations déjà enregistrées restent conservées.
- L’API d’un matériau inconnu répond avec le statut HTTP 404 au lieu d’une réponse 200 contenant une erreur.
- Le pied de page et l’API de santé utilisent directement la version du paquet Python afin d’éviter une divergence future.
- Le lien trompeur vers un « protocole complet » dans la bibliothèque personnelle a été remplacé par un lien vers les critères de validité réellement disponibles.

## Vérifications réalisées

- **102 tests automatisés** réussis.
- Compilation complète de l’application et de ses modules.
- **2 000 scénarios aléatoires** sur les 50 matériaux, avec températures de −40 à 160 °C, humidités de 0 à 100 %, plusieurs épaisseurs, horizons et seuils : aucune valeur non finie, aucune borne inversée et aucun module négatif.
- **150 scénarios systématiques** couvrant intérieur, extérieur et immersion pour les 50 matériaux.
- Contrôle visuel des pages à 1 280 px et sur un écran mobile de 390 px, sans débordement horizontal résiduel.
- Contrôle des titres de page, boutons, liens, identifiants du DOM et erreurs de console.
- Vérification de l’intégrité SQLite et des clés étrangères : aucun défaut détecté.
- Vérification des simulations enregistrées et de la génération des classeurs Excel et rapports PDF.
- Test de charge en lecture avec **30 utilisateurs simultanés et 90 requêtes** : aucune erreur.
- Vérification des liens scientifiques : les sources répondent ; IUPAC refuse seulement le client automatisé, sans indiquer un lien supprimé.

## Limites maintenues volontairement

La cohérence logicielle et numérique ne transforme pas une estimation documentaire en validation expérimentale. Le niveau de preuve reste affiché pour chaque résultat. Les profils de famille servent à la présélection ; le PP extérieur et l’IIR disposent de domaines documentaires plus précis, avec leurs fenêtres d’observation explicitement limitées.
