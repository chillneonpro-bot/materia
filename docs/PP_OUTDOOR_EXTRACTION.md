# Traçabilité des extractions PP extérieur

## Corpus utilisé

Le profil PP extérieur v0.23 combine trois publications. Chaque publication compte comme une unité de calibration, quel que soit le nombre de formulations qu’elle contient.

1. Matos et al., `10.3390/polym16131788` : quatre formulations PP H301, valeurs moyennes et écarts-types copiés directement du tableau 2 à 0, 30 et 120 jours.
2. Intapun et al., `10.3390/ma13040914` : PP vierge sans ZnO, six valeurs centrales numérisées depuis la figure 4 à 0, 3, 6, 12, 18 et 24 semaines.
3. Al-Shabanat, `10.5539/ijc.v3n1p129` : PP520L SABIC sans additif, quatre valeurs centrales numérisées depuis la figure 8 à 0, 2, 4 et 6 mois.

## Contrôles des figures

### Bangkok

- source : image JPEG de la figure 4 fournie par PubMed Central ;
- SHA-256 de l’image contrôlée : `c7179e062eb1572280dc0102948e19ceddd11e52f3550f0515f02f37e3595612` ;
- axe vertical : module de Young, 0 à 300 MPa par pas de 50 MPa ;
- temps : 0, 3, 6, 12, 18 et 24 semaines ;
- protocole : ASTM D638, PP injecté, 100 mm/min, exposition réelle à Bangkok, indice UV 8–14 et températures 22–39 °C ;
- incertitude de numérisation conservatrice : 2 %.

### Riyad

- source : PDF ouvert de l’article CCSE ;
- SHA-256 du PDF contrôlé : `fea9ebd8b40cbd4c11ce2c9675b2f907ebf0e7116ea3a5257d2c0d87740917a5` ;
- page 13, figure 8 ; axe vertical de 0 à 2 000 MPa par pas de 500 MPa ;
- temps : 0, 2, 4 et 6 mois, convertis avec 30,4375 jours par mois ;
- protocole : ASTM D638, PP520L injecté, 5 mm/min, exposition réelle à Riyad d’avril à septembre 2009 ;
- incertitude de numérisation conservatrice : 5 %.

Les valeurs numériques sont conservées dans `data/evidence/pp_outdoor_digitized.csv`. Les figures n’ayant pas de tableau numérique associé, ces points ne sont jamais marqués `direct_table_transcription`.

## Calibration

Les modules sont normalisés sous forme `E(t)/E0`. La fenêtre commune s’arrête à 120 jours. Pour chacune des trois publications, Materia retire toutes ses séries, reconstruit le profil avec les publications restantes et calcule les erreurs logarithmiques sur la publication retirée. Les quantiles 10 % et 90 % de ces erreurs donnent une bande asymétrique qui s’élargit avec le temps.

La couverture ponctuelle observée est de 83,3 % pour une cible de 80 %. Avec seulement trois publications, il s’agit d’un intervalle prédictif pilote. Les grades, stabilisants, géométries et climats restent hétérogènes.
