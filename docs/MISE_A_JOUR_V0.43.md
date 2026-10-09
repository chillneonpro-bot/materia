# Materia v0.43 — plage uniforme resserrée

La plage principale du simulateur est resserrée de ±20 % à **±10 % sur la vitesse de vieillissement**.

- vieillissement rapide : vitesse centrale `×1,10` ;
- vieillissement lent : vitesse centrale `×0,90` ;
- borne basse du temps au seuil : `temps central / 1,10` ;
- borne haute du temps au seuil : `temps central / 0,90`.

L’intervalle temporel représente ainsi environ **−9,1 % / +11,1 %** autour du temps central. La même règle est appliquée à tous les matériaux dans le simulateur et le comparateur.

La courbe centrale reste calculée avec les informations propres au matériau. Les erreurs et dispersions issues des publications restent conservées dans la page **Validité** et dans la traçabilité des exports. Cette plage resserrée est une convention de comparaison, pas une garantie statistique universelle.
