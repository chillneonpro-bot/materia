# Materia v0.12 — première mise en œuvre de l’audit

**Date :** 28 septembre 2026

## Livré

- page d’orientation vers trois parcours distincts ;
- projection exploratoire depuis une fiche matériau avec niveau de preuve, domaine, limites, facteurs et empreinte ;
- visualisation directe de quatre formulations PP publiées par MDPI, moyenne ± écart-type ;
- refus d’extrapoler les mesures publiées au-delà de 120 jours ;
- tableaux accessibles sous les graphiques et résumés en langage simple ;
- catalogue de 50 matériaux paginé et relié au simulateur ;
- durée affichée en années et mois ;
- projets compatibles avec les scénarios synthétiques et les projections, export global et suppression ;
- comparaison homogénéisée en jours ;
- espace classe pilote : cours, code, consignes, parcours demandé, remises et vue enseignant ;
- revue scientifique bloquée sans `MATERIA_REVIEW_TOKEN` ;
- autorisation exigée aussi dans la couche de données ;
- clés étrangères SQLite, index, attente d’écriture, schéma v2 et permissions locales restrictives ;
- contrôle de disponibilité `/health/readiness` ;
- 49 tests automatisés réussis.

## Limites conservées volontairement

- l’espace classe utilise une identité de session navigateur ;
- aucun SSO/OIDC/SAML n’est encore configuré ;
- les projections de fiche restent exploratoires ;
- la calibration PP couvre 120 jours et ne vaut pas validation d’une projection en années ;
- aucune observation candidate n’a encore été acceptée par un responsable scientifique ;
- SQLite et le stockage local des PDF restent adaptés à un pilote, pas à une production institutionnelle.

## Prochaine étape de production

La prochaine version doit connecter l’identité institutionnelle, déplacer les données partagées vers PostgreSQL, séparer les fichiers de la base, ajouter correction/notation et tester 30 sessions NiceGUI simultanées. La validation scientifique doit ensuite être menée domaine par domaine sur des campagnes indépendantes.
