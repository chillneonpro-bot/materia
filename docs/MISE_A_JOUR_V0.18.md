# Materia v0.18 — exports Excel complets

Cette version remplace les exports CSV des résultats par des classeurs `.xlsx` directement lisibles par les étudiants et exploitables dans Excel, LibreOffice ou un autre tableur compatible.

## Contenu d'un export de résultat

- une feuille **Synthèse** avec le matériau ou la formulation, le module initial, le module à l'horizon, le pourcentage conservé, le temps au seuil, le statut scientifique et la courbe native modifiable ;
- une feuille **Courbe** avec les 241 valeurs calculées, les bornes, la conservation du module et le seuil ;
- une feuille **Origine et méthode** avec les paramètres saisis, l'unité de l'horizon, la référence, le DOI, le protocole, la nature de l'incertitude, les avertissements, la version du modèle et l'empreinte SHA-256 ;
- une feuille **Mesures source** lorsque le calcul repose sur des observations acceptées ou publiées. Les valeurs d'origine restent séparées de l'interpolation.

## Comparaisons et listes

Les comparaisons de matériaux, de températures et de projets produisent aussi un classeur Excel. Il contient une synthèse commune, toutes les courbes exprimées en jours, un graphique de conservation du module et les sources propres à chaque scénario.

Le catalogue des matériaux et les notes de classe sont exportés dans des tableaux Excel filtrables. L'import de mesures expérimentales reste en CSV, car ce format simple sert de format d'échange pour les données brutes.

## Contrôles

- les chaînes commençant par un caractère de formule Excel sont neutralisées ;
- les graphiques restent liés aux tableaux du classeur ;
- la présence des feuilles, graphiques, sources et scénarios est testée automatiquement ;
- le classeur de référence a été rendu et relu visuellement sur les quatre feuilles ;
- la suite comprend 65 tests automatisés réussis.
