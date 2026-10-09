# Materia v0.39 — extension vérifiée du catalogue

Cette version porte le catalogue de **54 à 75 matériaux** et la bibliothèque de propriétés initiales de **12 à 21 profils**, couvrant **19 matériaux**.

## Nouveaux matériaux classés

- polymères styréniques : ASA, HIPS ;
- polymères haute performance : PPE, PPA, PEKK, PAEK ;
- élastomères thermoplastiques : TPC-ET, PEBA, TPV, TPS, TPO ;
- fluoropolymères et élastomères fluorés : FEP, PFA, ECTFE, FKM, FFKM ;
- polymères vinyliques et halogénés : CPVC, PVB, PVOH ;
- polyesters biodégradables : PBAT, PBSA.

Ces fiches taxonomiques permettent la recherche, le tri et une estimation exploratoire. Elles ne créent pas artificiellement une preuve de vieillissement.

## Nouveaux profils mécaniques recoupés

| Matériau | Grade ou domaine | Module retenu | Contrôle |
|---|---|---:|---|
| PET | TECAPET white | 3 100 MPa | page produit et brochure Ensinger |
| PEEK | VICTREX 450G | 4 000 MPa | page produit et fiche technique Victrex |
| PEI | ULTEM 1000 / TECAPEI natural | 3 200 MPa | SABIC et Ensinger |
| PSU | Ultrason S 3010 / TECASON S | 2 550–2 700 MPa | BASF et Ensinger |
| PESU | Ultrason E 2010 | 2 650 MPa | fiche et portail BASF |
| PVDF | TECAFLON PVDF / Kynar 720 | 2 200–2 300 MPa | Ensinger et Arkema |
| PPA | Ultramid Advanced N3U41G6 | 10 500 MPa | éditions anglaise et allemande BASF |
| PFA | poudre Daikin, comprimée ou PBF | 360–378 MPa | deux rapports Daikin |
| FEP | film Teflon FEP, 0,025 mm | 480 MPa | deux révisions Chemours |

## Règles de fiabilité appliquées

- aucune valeur n'est enregistrée sans deux supports officiels identifiés ;
- le grade, la norme, la température, le conditionnement et le procédé sont conservés ;
- les contrôles entre fabricants sont affichés comme une **plage de famille**, jamais comme l'équivalence de deux grades ;
- les contrôles entre éditions d'une même fiche sont signalés comme contrôles documentaires, pas comme mesures indépendantes ;
- les valeurs d'un film, d'une forme semi-finie, d'un composite renforcé ou d'une fabrication additive restent attachées à cette forme et à ce procédé ;
- un module initial vérifié ne valide pas la cinétique de vieillissement. Les courbes restent des estimations de présélection tant qu'aucune série temporelle comparable n'est disponible.

## Conséquence dans l'interface

Les 75 matériaux sont disponibles dans **Matériaux**, **Simuler** et **Comparer**. Pour les 19 matériaux munis d'un profil recoupé, Materia préremplit le module initial du grade documenté et affiche ses deux références. Les autres matériaux restent utilisables avec une valeur de famille clairement signalée ou une valeur saisie par l'utilisateur.
