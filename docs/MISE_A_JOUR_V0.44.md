# Materia v0.44 — plage totale de 10 %

La plage principale du simulateur couvre maintenant **10 % au total**, et non 10 % de chaque côté.

- borne lente : vitesse centrale `×0,95` ;
- courbe centrale : `×1,00` ;
- borne rapide : vitesse centrale `×1,05` ;
- borne basse du temps au seuil : `temps central / 1,05` ;
- borne haute du temps au seuil : `temps central / 0,95`.

L’intervalle temporel représente environ **−4,8 % / +5,3 %** autour du temps central. La même convention alimente le simulateur, le comparateur, les classeurs Excel, les PDF et les rapports JSON.

Cette plage est une convention de comparaison resserrée. Les dispersions et erreurs scientifiques propres aux publications restent conservées séparément dans la page **Validité**.
