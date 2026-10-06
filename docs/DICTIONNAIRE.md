# Dictionnaire CSV hygrothermique v2

CSV UTF-8 avec virgule comme séparateur. Toutes les colonnes ci-dessous sont obligatoires. Les données brutes restent conservées avec les valeurs normalisées.

| Colonne | Format et signification |
|---|---|
| experiment_id | Identifiant unique d'une expérience ; répétitions séparées |
| time | Nombre fini >= 0 |
| time_unit | days, hours ou seconds |
| modulus | Nombre fini strictement positif |
| modulus_unit | MPa, GPa ou Pa |
| initial_modulus | Module initial de référence E₀, nombre fini strictement positif |
| initial_modulus_unit | MPa, GPa ou Pa |
| temperature_C | Température de vieillissement, > -273,15 °C |
| humidity_RH | Humidité relative, entre 0 et 100 % |
| thickness_mm | Épaisseur de l’éprouvette en mm, strictement positive |
| measurement_temperature_C | Température d'essai, > -273,15 °C |
| material | Formulation ou identifiant déclaré |
| protocol | tensile uniquement pour ce prototype |
| source | DOI ou référence/identifiant de laboratoire ; déclaration non vérifiée |
| location | Page, tableau, figure ou emplacement exact |

Normalisation : heures, jours, MPa et propriété résiduelle `E/E₀`. La propriété résiduelle admise doit être strictement positive et inférieure ou égale à 2 afin de conserver les cas possibles de rigidification tout en détectant les erreurs d’unité. Pas de conversion entre protocoles. Une information inconnue ne doit pas être inventée pour contourner un champ obligatoire ; elle rend la série inadmissible à cet import restreint.

Maximum 2 Mo et 10 000 mesures. Doublons expérience–temps rejetés. Les mesures ont toutes le statut `pending`. Le prototype ne propose aucun bouton de validation scientifique.

La calibration exponentielle historique exige un matériau, une température de vieillissement, une température d'essai et un protocole uniques ; au moins quatre points et trois temps distincts. Chaque groupe contribue avec un poids total identique au critère quadratique en log-module.

La comparaison Machine Learning exige au moins 12 mesures et trois expériences indépendantes. Elle utilise température, humidité relative, temps d’exposition et épaisseur pour prédire `E/E₀`. Les plis de validation sont séparés par `experiment_id` avec `GroupKFold`. Elle compare Ridge, Random Forest et XGBoost lorsque son moteur natif est disponible ; sinon un Gradient Boosting Scikit-learn est explicitement signalé. Les sorties sont R², RMSE, MAE, écart apprentissage-validation et importance SHAP ou par permutation. Cette validation interne ne remplace pas un test externe par publication ou campagne indépendante.
