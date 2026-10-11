# Plan d’action pour une version publiable et simple

## Objectif produit

Un étudiant doit pouvoir obtenir et comprendre une estimation en moins de deux minutes, sans lire de documentation avant de commencer. L’écran principal doit répondre à trois questions : quel matériau, dans quelles conditions et pendant combien de temps ?

## Priorité 1 — simplifier le parcours principal

1. Limiter le formulaire visible à cinq entrées : matériau, milieu, température, horizon et seuil.
2. Préremplir le module initial depuis la fiche du matériau.
3. Ranger humidité, épaisseur, grade, procédé et liquide dans **Paramètres avancés**.
4. Conserver un seul bouton principal : **Calculer**.
5. Afficher immédiatement la courbe à droite sur ordinateur et sous le formulaire sur mobile.

Critère de validation : un nouvel utilisateur termine une simulation sans aide en moins de deux minutes.

## Priorité 2 — réduire le résultat à l’essentiel

L’écran par défaut contient seulement :

- le temps central au seuil ;
- la plage resserrée ;
- le module à l’horizon ;
- une courbe ;
- une phrase d’interprétation en français courant.

Supprimer de la vue principale les termes `P10`, `P50`, `P90`, les scores de correspondance, les niveaux sur quatre, les empreintes et les détails de calibration. Les conserver dans un seul volet **Méthode et sources**.

Critère de validation : aucune carte de résultat ne dépasse deux lignes d’explication.

## Priorité 3 — simplifier les actions

1. Remplacer les sept boutons d’export par un bouton **Exporter** ouvrant un menu : Excel, PDF et données.
2. Déplacer **Figer avant essais**, **Plan d’expérience** et **Carte de preuve** dans un mode **Recherche**.
3. Conserver **Enregistrer** comme seule action secondaire visible.
4. Dans Comparer, limiter la vue à deux ou trois matériaux et trois indicateurs communs.

Critère de validation : au maximum deux boutons visibles sous un résultat.

## Priorité 4 — simplifier la navigation

Navigation principale proposée :

1. **Accueil**
2. **Simuler**
3. **Comparer**
4. **Mes projets**

Regrouper Matériaux, Validité, Comprendre, Documents et Données dans **Ressources**. Afficher Espace classe et Administration uniquement aux utilisateurs concernés.

## Priorité 5 — préparer la publication

1. Finaliser les textes courts, la politique de confidentialité, la licence et les crédits des sources.
2. Tester les parcours sur Chrome, Edge et Safari, sur ordinateur et mobile.
3. Faire tester la version par dix étudiants et deux enseignants sans démonstration préalable.
4. Corriger tout blocage rencontré par au moins deux testeurs.
5. Ajouter suivi des erreurs, sauvegarde, restauration testée et environnement de production séparé.
6. Publier une version candidate, geler les fonctions pendant les essais utilisateurs, puis publier la v1.0.

## Indicateurs de sortie v1.0

- au moins 90 % des testeurs terminent une simulation sans aide ;
- temps médian inférieur à deux minutes ;
- aucune erreur bloquante sur les parcours Simuler, Comparer et Exporter ;
- interface utilisable au clavier et sur un écran mobile ;
- calcul, plage, source et version identiques dans l’interface et les exports ;
- sauvegarde restaurée avec succès avant la mise en production.

## Ordre recommandé

- Sprint 1 : formulaire, résultat et exports simplifiés.
- Sprint 2 : navigation, mobile, accessibilité et textes.
- Sprint 3 : tests utilisateurs, corrections, supervision et version candidate.
