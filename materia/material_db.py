"""Curated material registry, separated from model-training observations."""
from __future__ import annotations

import sqlite3
import hashlib
from datetime import date, datetime, timezone
from materia import store

SCHEMA_VERSION = 6

SOURCES = [
    {
        "id": "nims-polyinfo",
        "title": "NIMS Polymer Database PoLyInfo",
        "organization": "National Institute for Materials Science (NIMS)",
        "url": "https://polymer.nims.go.jp/en/",
        "doi": "10.1080/27660400.2024.2354649",
        "accessed": "2026-09-29",
        "scope": "Référentiel de structures, procédés, conditions de mesure et propriétés de polymères issues de la littérature.",
        "license_note": "Référence et consultation manuelle uniquement. Le téléchargement massif et le scraping sont interdits par le service.",
    },
    {
        "id": "nims-property-help",
        "title": "PoLyInfo — définition des propriétés mécaniques",
        "organization": "NIMS",
        "url": "https://polymer.nims.go.jp/PoLyInfo/guide/en/property.html",
        "doi": None,
        "accessed": "2026-09-29",
        "scope": "Définition du module en traction, unités et conditions de mesure.",
        "license_note": "Référence documentaire ; aucune valeur de propriété copiée automatiquement.",
    },
    {
        "id": "nist-weathering",
        "title": "Metrology for Accelerated Laboratory Weathering",
        "organization": "National Institute of Standards and Technology (NIST)",
        "url": "https://www.nist.gov/programs-projects/metrology-accelerated-laboratory-weathering",
        "doi": None,
        "accessed": "2026-09-29",
        "scope": "Indique des travaux/données de validation sur PE, PET et systèmes époxy/polyester ; ne publie pas les séries numériques sur cette page.",
        "license_note": "Source institutionnelle publique. Les données numériques restent à obtenir et vérifier.",
    },
    {
        "id": "ldpe-photooxidation-model",
        "title": "Physics-based Constitutive Modeling of Photo-oxidative Aging in Semi-Crystalline Polymers",
        "organization": "Publication scientifique / prépublication",
        "url": "https://arxiv.org/abs/2108.07143",
        "doi": "10.48550/arXiv.2108.07143",
        "accessed": "2026-09-29",
        "scope": "Modélisation physique reliant photo-oxydation et réponse mécanique du LDPE.",
        "license_note": "Référence candidate à examiner manuellement avant extraction de données.",
    },
    {
        "id": "scida-2013-flax-epoxy",
        "title": "Influence of hygrothermal ageing on the damage mechanisms of flax-fibre reinforced epoxy composite",
        "organization": "Composites Part B / Université de Reims Champagne-Ardenne",
        "url": "https://doi.org/10.1016/j.compositesb.2012.12.010",
        "doi": "10.1016/j.compositesb.2012.12.010",
        "accessed": "2026-09-29",
        "scope": "Module de Young en traction après vieillissement à 90 % HR, 20/40 °C, plaque de 2,5 mm ; cinq temps visibles dans la figure 4.",
        "license_note": "Valeurs intermédiaires numérisées depuis la figure 4 et soumises à revue ; valeurs initiales/finales confirmées dans le texte.",
    },
    {
        "id": "nims-taxonomy",
        "title": "PoLyInfo — Taxonomy, Definitions and Rules for Classification",
        "organization": "National Institute for Materials Science (NIMS)",
        "url": "https://polymer.nims.go.jp/PoLyInfo/guide/en/pdf/TaxonomyDefinition.pdf",
        "doi": None,
        "accessed": "2026-09-23",
        "scope": "Classification structurale des polymères en niveaux hiérarchiques.",
        "license_note": "Référentiel de classification consulté manuellement ; aucune extraction massive de propriétés.",
    },
    {
        "id": "iupac-goldbook",
        "title": "IUPAC Compendium of Chemical Terminology — Gold Book",
        "organization": "International Union of Pure and Applied Chemistry (IUPAC)",
        "url": "https://goldbook.iupac.org/",
        "doi": "10.1351/goldbook",
        "accessed": "2026-09-23",
        "scope": "Terminologie de référence pour polymères, réseaux, thermodurcissables et élastomères thermoplastiques.",
        "license_note": "Référence terminologique officielle.",
    },
    {
        "id": "mdpi-pp-natural-aging-2024",
        "title": "Natural Aging of Reprocessed Polypropylene Composites Filled with Sustainable Corn Fibers",
        "organization": "MDPI Polymers",
        "url": "https://www.mdpi.com/2073-4360/16/13/1788",
        "doi": "10.3390/polym16131788",
        "accessed": "2026-09-29",
        "scope": "Module de Young du grade PP H301 retransformé une ou trois fois, avec ou sans fibres de balle de maïs, après 0, 30 et 120 jours de vieillissement naturel ; ASTM D638, 50 mm/min, moyenne ± écart-type, n=7.",
        "license_note": "Article en libre accès CC BY 4.0 ; valeurs transcrites directement du tableau 2.",
    },
    {
        "id": "mdpi-pp-opoka-aging-2022",
        "title": "The Accelerated Aging Impact on Mechanical and Thermal Properties of Polypropylene Composites with Sedimentary Rock Opoka-Hybrid Natural Filler",
        "organization": "MDPI Materials / PubMed Central",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8745994/",
        "doi": "10.3390/ma15010338",
        "accessed": "2026-09-29",
        "scope": "Module de Young relatif de PP et composites après 0 à 1 000 h de vieillissement accéléré.",
        "license_note": "Article en libre accès CC BY 4.0 ; les valeurs temporelles de module sont publiées dans une figure et exigent une numérisation contrôlée.",
    },
    {
        "id": "mdpi-ipp-natural-aging-2020",
        "title": "Investigation on Microstructures and Mechanical Properties of Isotactic Polypropylene Parts Fabricated by Different Process Conditions with Different Aging Periods",
        "organization": "MDPI Polymers / PubMed Central",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7760983/",
        "doi": "10.3390/polym12122828",
        "accessed": "2026-09-29",
        "scope": "Vieillissement naturel de pièces iPP à 0, 6 et 12 mois selon plusieurs conditions de mise en œuvre.",
        "license_note": "Article en libre accès CC BY 4.0 ; la propriété mécanique temporelle principale est la résistance en traction, pas le module de Young.",
    },
    {
        "id": "mdpi-pp-film-natural-aging-2022",
        "title": "Aging Study of Plastics to Be Used as Radiative Cooling Wind-Shields for Night-Time Radiative Cooling—Polypropylene as an Alternative to Polyethylene",
        "organization": "MDPI Energies / Universitat de Lleida",
        "url": "https://www.mdpi.com/1996-1073/15/22/8340",
        "doi": "10.3390/en15228340",
        "accessed": "2026-09-30",
        "scope": "Film PP-35 de 35,8 µm, exposition naturelle 90 jours à Lleida, essais ISO 527, cinq éprouvettes.",
        "license_note": "Article en libre accès CC BY 4.0 ; source indépendante qualifiée, mais données incompatibles avec une validation directe du PP H301 retransformé.",
    },
    {
        "id": "mdpi-iir-mwf-2019",
        "title": "Butyl Rubber-Based Composite: Thermal Degradation and Prediction of Service Lifetime",
        "organization": "MDPI Journal of Composites Science",
        "url": "https://www.mdpi.com/2504-477X/3/2/48",
        "doi": "10.3390/jcs3020048",
        "accessed": "2026-09-30",
        "scope": "Composite de caoutchouc butyle chargé de noir de carbone, immergé dans le fluide d’usinage Milform 64 SST à 80, 100 et 120 °C ; module publié à 0–24 h et durée fondée sur la force de traction.",
        "license_note": "Article en libre accès CC BY 4.0 ; tableaux numériques vérifiables. Le domaine 80–120 °C, le fluide et la propriété de fin de vie interdisent un transfert direct vers l’eau à 23 °C.",
    },
    {
        "id": "mdpi-pp-zno-sunlight-2020",
        "title": "Polypropylene/ZnO Nanocomposites: Mechanical Properties, Photocatalytic Dye Degradation, and Antibacterial Property",
        "organization": "MDPI Materials / PubMed Central",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7078909/",
        "doi": "10.3390/ma13040914",
        "accessed": "2026-09-30",
        "scope": "PP injecté avec 0 à 2 % de ZnO, exposé au soleil à Bangkok pendant 24 semaines ; module de Young ASTM D638 à 0, 3, 6, 12, 18 et 24 semaines.",
        "license_note": "Article en libre accès CC BY 4.0 ; valeurs centrales numérisées depuis la figure 4 et conservées avec une incertitude d’extraction.",
    },
    {
        "id": "ccse-pp-riyadh-weathering-2011",
        "title": "Study of the Effect of Weathering in Natural Environment on Polypropylene and Its Composites",
        "organization": "International Journal of Chemistry / CCSE",
        "url": "https://ccsenet.org/journal/index.php/ijc/article/view/6705",
        "doi": "10.5539/ijc.v3n1p129",
        "accessed": "2026-09-30",
        "scope": "PP520L SABIC injecté, exposé naturellement à Riyad d’avril à septembre 2009 ; module de Young ASTM D638 tous les deux mois jusqu’à six mois.",
        "license_note": "Article ouvert sous CC BY 4.0 ; valeurs centrales numérisées depuis la figure 8 et conservées avec une incertitude d’extraction.",
    },
]

# Manufacturer documents are kept as individual sources so a property value can
# be checked against a second official page or document without pretending that
# two commercial grades are the same material.
SOURCES += [
    dict(id='lyb-moplen-hp501l',title='Moplen HP501L — product page',organization='LyondellBasell',
         url='https://www.lyondellbasell.com/en/polymers/p/Moplen-HP501L/3098c7db-4396-4df2-9866-4258741c0f19',doi=None,accessed='2026-10-06',
         scope='PP homopolymère commercial ; module en traction publié pour le grade HP501L.',license_note='Fiche fabricant officielle ; valeurs typiques, non garanties.'),
    dict(id='lyb-pp-selection-guide',title='Polypropylene grades used in sheet extrusion and thermoforming',organization='LyondellBasell',
         url='https://www.lyondellbasell.com/4a7b15/globalassets/sites/lyb-documents/op/pp/polypropylenegrades-used-in-sheet-extrusion-and-thermoforming-applications.pdf',doi=None,accessed='2026-10-06',
         scope='Guide officiel multi-grades PP ; méthode ISO 527 et valeurs à 23 °C.',license_note='Document fabricant officiel ; valeurs typiques.'),
    dict(id='covestro-makrolon-2407-tds',title='Makrolon 2407 — product data',organization='Covestro',
         url='https://solutions.covestro.com/en/products/makrolon/makrolon-2407_000000000086286874',doi=None,accessed='2026-10-06',
         scope='Polycarbonate Makrolon 2407 ; propriétés mécaniques ISO à 23 °C / 50 % HR.',license_note='Page fabricant officielle ; valeurs caractéristiques.'),
    dict(id='covestro-makrolon-2407-page',title='Makrolon — official product range',organization='Covestro',
         url='https://solutions.covestro.com/-/media/covestro/solution-center/brands/downloads/imported/1556888808.pdf',doi=None,accessed='2026-10-06',
         scope='Tableau officiel de gamme confirmant la valeur du grade 2407.',license_note='Document fabricant officiel.'),
    dict(id='ineos-terluran-gp22',title='Terluran GP-22 — product data',organization='INEOS Styrolution',
         url='https://www.ineos-styrolution.com/Product/Terluran_Terluran-GP-22_SKU300600120827_lang_de_DE.html',doi=None,accessed='2026-10-06',
         scope='ABS Terluran GP-22 ; module en traction ISO 527.',license_note='Page fabricant officielle ; valeurs typiques du produit naturel.'),
    dict(id='ineos-terluran-range',title='Terluran ABS — product range',organization='INEOS Styrolution',
         url='https://www.ineos-styrolution.com/Product/Terluran_ID30060012_lang_ja_JP.html',doi=None,accessed='2026-10-06',
         scope='Tableau officiel de la gamme confirmant le module du GP-22.',license_note='Page fabricant officielle.'),
    dict(id='basf-ultradur-b4520',title='Ultradur B 4520 — Product Datasheet',organization='BASF',
         url='https://download.basf.com/p1/8a8081c57fd4b609017fd62e21255407/en/ULTRADUR%25C2%25AE_B4520',doi=None,accessed='2026-10-06',
         scope='PBT non renforcé B 4520 ; module en traction ISO 527.',license_note='Fiche fabricant officielle ; valeurs typiques.'),
    dict(id='basf-ultradur-b4520-black',title='Ultradur B 4520 BK00110 — Product information',organization='BASF',
         url='https://pmtools-na.basf.com/products/dspdf.php?autospec=1&param=Ultradur+B+4520+BK00110&type=iso',doi=None,accessed='2026-10-06',
         scope='Version noire du B 4520, contrôle du module à 23 °C.',license_note='Fiche fabricant officielle.'),
    dict(id='basf-ultramid-a3k',title='Ultramid A3K — Product Datasheet',organization='BASF',
         url='https://download.basf.com/p1/8a8082587fd4b608017fd64108ab6d3b/en/ULTRAMID%3Csup%3E%C2%AE%3Csup%3E_A3K_Product_Data_Sheet_Asia_PacificEurope_English.pdf',doi=None,accessed='2026-10-06',
         scope='PA66 A3K ; module ISO 527 à sec et conditionné.',license_note='Fiche fabricant officielle ; valeurs typiques.'),
    dict(id='basf-ultramid-a3k-r01',title='Ultramid A3K R01 — Product Datasheet',organization='BASF',
         url='https://download.basf.com/p1/8a8081c57fd4b609017fd6402ca60778/en/ULTRAMID%25C2%25AE_A3K_R01',doi=None,accessed='2026-10-06',
         scope='Révision A3K R01 ; contrôle des valeurs à sec et conditionnées.',license_note='Fiche fabricant officielle.'),
    dict(id='basf-ultraform-n2320',title='Ultraform N2320 003 PRO AT — medical solutions data',organization='BASF',
         url='https://download.basf.com/p1/8a8081c57fd4b609018021fe1bcc1c95/en/Ultraform%253Csup%253E%25C2%25AE%253Csup%253E_PRO_%2528POM%2529_and_Ultradur%253Csup%253E%25C2%25AE%253Csup%253E_PRO_%2528PBT%2529_-_Engineering_Plastics_for_Medical_Solutions',doi=None,accessed='2026-10-06',
         scope='POM copolymère non renforcé ; module ISO 527.',license_note='Document fabricant officiel.'),
    dict(id='celanese-hostaform-c9021',title='Hostaform POM product manual',organization='Celanese',
         url='https://www.celanese.com/-/media/cewebjssapp/project/marketodocuments/POM-065-HostaformPOMEU-PM-EN.pdf',doi=None,accessed='2026-10-06',
         scope='POM copolymère C 9021 ; contrôle inter-fabricants du domaine de module.',license_note='Manuel fabricant officiel ; valeurs typiques.'),
    dict(id='topas-6013m07-tds',title='TOPAS 6013M-07 — Technical Data Sheet',organization='TOPAS Advanced Polymers / Daicel',
         url='https://topas.com/wp-content/uploads/2023/05/TDS_6013M-07_english-units.pdf',doi=None,accessed='2026-10-06',
         scope='COC 6013M-07 ; module en traction ISO 527.',license_note='Fiche fabricant officielle ; conversion kpsi vers MPa conservée.'),
    dict(id='topas-product-brochure',title='TOPAS COC Product Brochure',organization='TOPAS Advanced Polymers / Daicel',
         url='https://topas.com/wp-content/uploads/2023/05/TOPAS_Product-Brochure.pdf',doi=None,accessed='2026-10-06',
         scope='Tableau multi-grades COC sous ISO 291 23/50, utilisé comme contrôle croisé.',license_note='Brochure fabricant officielle.'),
    dict(id='ensinger-tecason-p',title='TECASON P PPSU — technical data',organization='Ensinger',
         url='https://www.ensingerplastics.com/en-us/shapes/ppsu-tecason-p-black',doi=None,accessed='2026-10-06',
         scope='PPSU TECASON P ; module à 23 °C et propriétés de forme semi-finie.',license_note='Page et fiche fabricant officielles.'),
    dict(id='syensqo-radel-design',title='Radel PPSU Design Guide',organization='Syensqo',
         url='https://www.syensqo.com/sites/g/files/alwlxe161/files/2018-07/Radel-PPSU-Veradel-PESU-Acudel-PPSU-Design-Guide_EN.pdf',doi=None,accessed='2026-10-06',
         scope='PPSU Radel R-5000 ; contrôle inter-fabricants du module ASTM D638.',license_note='Guide fabricant officiel ; conversion kpsi vers MPa conservée.'),
    dict(id='arkema-rilsan-kno-t3l',title='Rilsan KNO T3L — Technical Data Sheet',organization='Arkema',
         url='https://hpp.arkema.com/assets/arkema/TDS_RILSAN%C2%AE%20KNO%20T3L_en_WW.pdf',doi=None,accessed='2026-10-06',
         scope='PA11 KNO T3L ; module ISO 527 à sec et conditionné.',license_note='Fiche fabricant officielle ; valeurs typiques.'),
    dict(id='arkema-rilsan-kno-t3l-ja',title='Rilsan KNO T3L — Technical Data Sheet (Japanese edition)',organization='Arkema',
         url='https://hpp.arkema.com/assets/arkema/TDS_RILSAN%C2%AE%20KNO%20T3L_ja_WW.pdf',doi=None,accessed='2026-10-06',
         scope='Seconde édition officielle du même grade ; contrôle des valeurs ISO 527 à sec et conditionné.',license_note='Fiche fabricant officielle ; valeurs typiques.'),
    dict(id='arkema-rilsan-brochure',title='Rilsan Polyamide 11 — General Brochure',organization='Arkema',
         url='https://www.arkema.com/files/live/sites/shared_arkema/files/downloads/countries/Japan/20230804_Rilsan-Pebax-brochures/RILSAN%C2%AE%20General%20Brochure_size%20reduced.pdf',doi=None,accessed='2026-10-06',
         scope='Comparaison officielle de grades PA11 sous ISO 527.',license_note='Brochure fabricant officielle.'),
    dict(id='zeon-cop-properties-cn',title='ZEONEX COP — characteristic properties',organization='Zeon Corporation',
         url='https://www.zeon.co.jp/cn/business/enterprise/pdf/200323392.pdf',doi=None,accessed='2026-10-06',
         scope='COP ZEONEX 480R ; module en traction ISO 527.',license_note='Tableau fabricant officiel ; valeurs typiques, non garanties.'),
    dict(id='zeon-cop-properties-en',title='ZEONEX characteristic properties — English',organization='Zeon Corporation',
         url='https://www.zeon.co.jp/en/business/enterprise/resin/pdf/200323391.pdf',doi=None,accessed='2026-10-06',
         scope='Version officielle anglaise de contrôle du grade 480R.',license_note='Document fabricant officiel.'),
]

RESEARCH_CANDIDATES = [
    {
        "id": "PP-OPOKA-2022", "material_id": "PP", "source_id": "mdpi-pp-opoka-aging-2022",
        "target_property": "Module de Young relatif", "exposure": "Vieillissement accéléré UV, 0–1 000 h",
        "status": "figure_digitization_required",
        "reason": "Les valeurs initiales sont tabulées, mais l’évolution temporelle du module est donnée sous forme de coefficients K dans la figure 2A. Une numérisation avec contrôle croisé est requise.",
        "next_action": "Numériser les quatre séries, conserver l’image et les points de contrôle, puis faire relire l’extraction.",
    },
    {
        "id": "IPP-NATURAL-2020", "material_id": "PP", "source_id": "mdpi-ipp-natural-aging-2020",
        "target_property": "Résistance en traction", "exposure": "Vieillissement naturel, 0–12 mois",
        "status": "target_property_mismatch",
        "reason": "La campagne documente la résistance en traction et la cristallinité, mais pas une série temporelle de module de Young compatible avec l’objectif actuel.",
        "next_action": "Conserver comme preuve contextuelle ; ne pas mélanger cette propriété avec le module de Young.",
    },
    {
        "id": "PP-FILM-NATURAL-2022", "material_id": "PP", "source_id": "mdpi-pp-film-natural-aging-2022",
        "target_property": "Module de Young en traction", "exposure": "Vieillissement naturel, 0 et 90 jours",
        "status": "domain_mismatch_excluded",
        "reason": "Le film PP-35, son épaisseur, ses directions d’essai et son usage diffèrent du grade H301 retransformé. Certaines comparaisons à 90 jours changent aussi d’orientation d’éprouvette.",
        "next_action": "Conserver comme preuve indépendante contextuelle ; ne pas l’utiliser pour calculer une erreur de validation du corpus H301.",
    },
    {
        "id": "IIR-MWF-2019", "material_id": "IIR", "source_id": "mdpi-iir-mwf-2019",
        "target_property": "Module de Young et force de traction", "exposure": "Immersion Milform 64 SST, 80–120 °C, 0–24 h",
        "status": "source_verified_domain_limited",
        "reason": "Les valeurs expérimentales du module sont intégrées. Elles permettent une interpolation entre 80 et 120 °C jusqu’à 24 h, mais aucun transfert sous 80 °C ni vers un autre liquide.",
        "next_action": "Obtenir une source indépendante et des temps plus longs avant de calibrer un intervalle prédictif ou une extrapolation à température ambiante.",
    },
]

MATERIALS = [
    dict(id="PE", name="Polyéthylène", abbreviation="PE", family="Polyoléfine", subtype="Famille générique", priority=1,
         mechanisms="Photo-oxydation; thermo-oxydation", target_property="Module de Young en traction",
         readiness="source_identified", source_id="nist-weathering",
         note="Famille citée par le NIST pour des données de validation. Une formulation/grade précis reste indispensable."),
    dict(id="LDPE", name="Polyéthylène basse densité", abbreviation="LDPE", family="Polyoléfine", subtype="Thermoplastique semi-cristallin", priority=1,
         mechanisms="Photo-oxydation; thermo-oxydation", target_property="Module de Young en traction",
         readiness="candidate_literature", source_id="ldpe-photooxidation-model",
         note="Candidat initial pour un modèle photo-oxydatif. Aucune courbe numérique validée n'est encore intégrée."),
    dict(id="PET", name="Poly(éthylène téréphtalate)", abbreviation="PET", family="Polyester", subtype="Thermoplastique", priority=1,
         mechanisms="Hydrolyse; photo-oxydation; thermo-oxydation", target_property="Module de Young en traction",
         readiness="source_identified", source_id="nist-weathering",
         note="Famille citée par le NIST pour la validation d'expositions accélérées et naturelles."),
    dict(id="EPOXY", name="Résine époxy", abbreviation="Époxy", family="Thermodurcissable", subtype="Système réticulé", priority=1,
         mechanisms="Photo-oxydation; thermo-oxydation; humidité", target_property="Module de Young en traction",
         readiness="source_identified", source_id="nist-weathering",
         note="Le durcisseur, la stœchiométrie et le cycle de cuisson doivent être définis avant toute modélisation."),
    dict(id="PP", name="Polypropylène", abbreviation="PP", family="Polyoléfine", subtype="Thermoplastique semi-cristallin", priority=2,
         mechanisms="Photo-oxydation; thermo-oxydation", target_property="Module de Young en traction",
         readiness="taxonomy_only", source_id="nims-polyinfo",
         note="Entrée documentaire. Aucune série temporelle admissible n'est intégrée."),
    dict(id="PA66", name="Polyamide 66", abbreviation="PA66", family="Polyamide", subtype="Thermoplastique semi-cristallin", priority=2,
         mechanisms="Thermo-oxydation; hydrolyse; humidité", target_property="Module de Young en traction",
         readiness="taxonomy_only", source_id="nims-polyinfo",
         note="L'humidité et la température de conditionnement doivent être enregistrées avec la mesure."),
    dict(id="PLA", name="Acide polylactique", abbreviation="PLA", family="Polyester biodégradable", subtype="Thermoplastique", priority=2,
         mechanisms="Hydrolyse; vieillissement physique", target_property="Module de Young en traction",
         readiness="taxonomy_only", source_id="nims-polyinfo",
         note="Entrée documentaire. La cristallinité et le milieu d'exposition sont des variables critiques."),
    dict(id="FLAX_EPOXY", name="Composite fibres de lin / époxy", abbreviation="Lin/époxy", family="Composite biosourcé", subtype="Stratifié 11 plis", priority=1,
         mechanisms="Absorption d’eau; plastification; endommagement fibre/matrice", target_property="Module de Young longitudinal en traction",
         readiness="data_pending_review", source_id="scida-2013-flax-epoxy",
         note="Plaque 11 plis, 44 % vol. de fibres, épaisseur 2,5 mm. Série candidate numérisée depuis la figure 4 de Scida et al."),
]

def _tax(ident: str, name: str, family: str, subtype: str, mechanisms: str, priority: int = 3) -> dict:
    return dict(id=ident,name=name,abbreviation=ident,family=family,subtype=subtype,priority=priority,
        mechanisms=mechanisms,target_property="Module de Young en traction",readiness="taxonomy_only",
        source_id="nims-polyinfo",note="Fiche documentaire initiale. Grade, formulation, procédé et protocole doivent être précisés avant modélisation.")

MATERIALS += [
    _tax('HDPE','Polyéthylène haute densité','Polyoléfine','Thermoplastique semi-cristallin','Photo-oxydation; thermo-oxydation',2),
    _tax('UHMWPE','Polyéthylène ultra-haute masse molaire','Polyoléfine','Thermoplastique semi-cristallin','Oxydation; fluage; irradiation'),
    _tax('PEX','Polyéthylène réticulé','Polyoléfine','Réseau réticulé','Thermo-oxydation; hydrolyse; fluage'),
    _tax('EVA','Éthylène-acétate de vinyle','Copolymère','Thermoplastique souple','Photo-oxydation; hydrolyse; thermo-oxydation'),
    _tax('PVC','Polychlorure de vinyle','Polymère vinylique','Thermoplastique amorphe','Déshydrochloration; photo-oxydation; perte de plastifiant',2),
    _tax('PS','Polystyrène','Polymère styrénique','Thermoplastique amorphe','Photo-oxydation; vieillissement physique'),
    _tax('ABS','Acrylonitrile-butadiène-styrène','Polymère styrénique','Thermoplastique multiphasé','Photo-oxydation; thermo-oxydation'),
    _tax('SAN','Styrène-acrylonitrile','Polymère styrénique','Copolymère amorphe','Photo-oxydation; thermo-oxydation'),
    _tax('PC','Polycarbonate','Polymère technique','Thermoplastique amorphe','Hydrolyse; photo-oxydation; vieillissement physique',2),
    _tax('PMMA','Poly(méthacrylate de méthyle)','Polymère acrylique','Thermoplastique amorphe','Photo-dégradation; vieillissement physique'),
    _tax('POM','Polyoxyméthylène','Polymère technique','Thermoplastique semi-cristallin','Thermo-oxydation; hydrolyse'),
    _tax('PA6','Polyamide 6','Polyamide','Thermoplastique semi-cristallin','Hydrolyse; humidité; thermo-oxydation',2),
    _tax('PA12','Polyamide 12','Polyamide','Thermoplastique semi-cristallin','Hydrolyse; humidité; thermo-oxydation'),
    _tax('PBT','Polybutylène téréphtalate','Polyester','Thermoplastique semi-cristallin','Hydrolyse; thermo-oxydation'),
    _tax('PPS','Polysulfure de phénylène','Polymère haute performance','Thermoplastique semi-cristallin','Thermo-oxydation; vieillissement thermique'),
    _tax('PEEK','Polyétheréthercétone','Polymère haute performance','Thermoplastique semi-cristallin','Vieillissement thermique; irradiation; humidité'),
    _tax('PEI','Polyétherimide','Polymère haute performance','Thermoplastique amorphe','Hydrolyse; vieillissement thermique'),
    _tax('PSU','Polysulfone','Polymère haute performance','Thermoplastique amorphe','Hydrolyse; vieillissement thermique'),
    _tax('PESU','Polyéthersulfone','Polymère haute performance','Thermoplastique amorphe','Hydrolyse; vieillissement thermique'),
    _tax('PTFE','Polytétrafluoroéthylène','Fluoropolymère','Thermoplastique semi-cristallin','Fluage; irradiation; vieillissement thermique'),
    _tax('PVDF','Polyfluorure de vinylidène','Fluoropolymère','Thermoplastique semi-cristallin','Irradiation; vieillissement thermique; fatigue'),
    _tax('TPU','Polyuréthane thermoplastique','Polyuréthane','Élastomère thermoplastique','Hydrolyse; photo-oxydation; humidité',2),
    _tax('PUR','Polyuréthane','Polyuréthane','Thermodurcissable ou mousse','Hydrolyse; photo-oxydation; thermo-oxydation'),
    _tax('EPDM','Éthylène-propylène-diène','Élastomère','Caoutchouc réticulé','Thermo-oxydation; ozone; humidité',2),
    _tax('NBR','Caoutchouc nitrile','Élastomère','Caoutchouc réticulé','Thermo-oxydation; huiles; ozone',2),
    _tax('SBR','Styrène-butadiène','Élastomère','Caoutchouc réticulé','Thermo-oxydation; ozone; fatigue'),
    _tax('SILICONE','Élastomère silicone','Élastomère','Polysiloxane réticulé','Vieillissement thermique; humidité; irradiation'),
    _tax('UP','Résine polyester insaturée','Thermodurcissable','Réseau réticulé','Hydrolyse; photo-oxydation; humidité'),
    _tax('VE','Résine vinylester','Thermodurcissable','Réseau réticulé','Hydrolyse; humidité; photo-oxydation'),
    _tax('PHENOLIC','Résine phénolique','Thermodurcissable','Réseau réticulé','Vieillissement thermique; oxydation; humidité'),
    _tax('PBS','Polybutylène succinate','Polymère biodégradable','Polyester thermoplastique','Hydrolyse; biodégradation; vieillissement physique'),
    _tax('PHA','Polyhydroxyalcanoate','Polymère biodégradable','Biopolyester','Hydrolyse; biodégradation; vieillissement physique'),
    _tax('PI','Polyimide','Polyimide','Polymère haute performance','Hydrolyse; thermo-oxydation; irradiation'),
    _tax('PAI','Polyamide-imide','Polyimide','Polymère haute performance','Vieillissement thermique; humidité'),
    _tax('LCP','Polymère à cristaux liquides','Polymère haute performance','Thermoplastique anisotrope','Vieillissement thermique; hydrolyse'),
    _tax('PAN','Polyacrylonitrile','Polymère vinylique','Thermoplastique semi-cristallin','Thermo-oxydation; photo-oxydation'),
    _tax('PVDC','Polychlorure de vinylidène','Polymère halogéné','Thermoplastique barrière','Déshydrochloration; vieillissement thermique'),
    _tax('PCL','Polycaprolactone','Polymère biodégradable','Polyester thermoplastique','Hydrolyse; biodégradation; vieillissement physique'),
    _tax('NR','Caoutchouc naturel','Élastomère','Polyisoprène réticulé','Ozone; thermo-oxydation; fatigue'),
    _tax('CR','Polychloroprène','Élastomère','Caoutchouc réticulé','Ozone; thermo-oxydation; humidité'),
    _tax('IIR','Caoutchouc butyle','Élastomère','Caoutchouc réticulé','Thermo-oxydation; ozone; fluage'),
    _tax('ETFE','Éthylène-tétrafluoroéthylène','Fluoropolymère','Copolymère thermoplastique','Irradiation; vieillissement thermique; fatigue'),
    dict(id='COC',name='Copolymère cyclo-oléfinique',abbreviation='COC',family='Polyoléfine cyclique',
         subtype='Thermoplastique amorphe',priority=2,mechanisms='Photo-oxydation; vieillissement thermique; vieillissement physique',
         target_property='Module de Young en traction',readiness='verified_datasheet',source_id='topas-6013m07-tds',
         note='Le module initial du grade TOPAS 6013 est recoupé entre une fiche technique et la brochure officielle. La cinétique reste à documenter.'),
    dict(id='COP',name='Polymère cyclo-oléfinique',abbreviation='COP',family='Polyoléfine cyclique',
         subtype='Thermoplastique amorphe',priority=2,mechanisms='Photo-oxydation; vieillissement thermique; vieillissement physique',
         target_property='Module de Young en traction',readiness='verified_datasheet',source_id='zeon-cop-properties-en',
         note='Le module initial du grade ZEONEX 480R est recoupé dans deux éditions officielles du tableau fabricant. La cinétique reste à documenter.'),
    dict(id='PPSU',name='Polyphénylsulfone',abbreviation='PPSU',family='Polymère haute performance',
         subtype='Thermoplastique amorphe',priority=2,mechanisms='Hydrolyse; vieillissement thermique; fatigue',
         target_property='Module de Young en traction',readiness='verified_datasheet',source_id='ensinger-tecason-p',
         note='Le domaine du module initial est recoupé entre deux grades PPSU de fabricants distincts. La cinétique reste à documenter.'),
    dict(id='PA11',name='Polyamide 11',abbreviation='PA11',family='Polyamide',
         subtype='Thermoplastique semi-cristallin biosourcé',priority=2,mechanisms='Hydrolyse; humidité; thermo-oxydation',
         target_property='Module de Young en traction',readiness='verified_datasheet',source_id='arkema-rilsan-kno-t3l',
         note='Les modules à sec et conditionné sont conservés séparément. Le procédé et l’humidité doivent accompagner toute comparaison.'),
]

THERMOSETS={'EPOXY','UP','VE','PHENOLIC','PUR'}
ELASTOMERS={'EPDM','NBR','SBR','SILICONE','NR','CR','IIR'}
TPE={'TPU'}
BIO={'PLA','PBS','PHA','PCL'}
COMPOSITES={'FLAX_EPOXY'}

def classification(material: dict) -> tuple[str,str,str]:
    ident=material['id']
    if ident in COMPOSITES: return 'Composite','Composite à fibres naturelles','experimental_pending'
    if ident in THERMOSETS: return 'Polymère thermodurcissable',material['family'],'taxonomy_verified'
    if ident in ELASTOMERS: return 'Élastomère',material['family'],'taxonomy_verified'
    if ident in TPE: return 'Élastomère thermoplastique',material['family'],'taxonomy_verified'
    if ident in BIO: return 'Thermoplastique biodégradable',material['family'],'taxonomy_verified'
    return 'Polymère thermoplastique',material['family'],'taxonomy_verified'

CANDIDATE_OBSERVATIONS = [
    # Figure 4 digitization. Exact textual anchors: E0=26.6 GPa; day 38=12.0/11.2 GPa.
    dict(experiment_id='SCIDA-20C-90RH', temperature_C=20., humidity_RH=90., thickness_mm=2.5,
         values=[(0,26600),(1,24400),(3,17800),(9,12700),(38,12000)]),
    dict(experiment_id='SCIDA-40C-90RH', temperature_C=40., humidity_RH=90., thickness_mm=2.5,
         values=[(0,26600),(1,24000),(3,17400),(9,11400),(38,11200)]),
]

MDPI_PP_OBSERVATIONS = [
    ('MDPI-RPP1X', [(0,604.1,9.0),(30,561.8,40.3),(120,555.8,20.5)]),
    ('MDPI-RPP3X', [(0,516.9,10.9),(30,465.2,21.4),(120,454.9,30.2)]),
    ('MDPI-RPP3X-3CHF', [(0,537.1,9.9),(30,504.9,20.1),(120,488.8,15.8)]),
    ('MDPI-RPP3X-5CHF', [(0,541.1,8.4),(30,492.4,30.9),(120,481.6,40.1)]),
]

# Table 2, experimental Young modulus E_exp in MPa (mean, standard deviation).
# The second OCR-visible "2 h" row is the 3 h row in the ordered source table.
MDPI_IIR_MWF_OBSERVATIONS = [
    (80., [(0,3.40,.04),(1,2.89,.20),(2,2.64,.16),(3,2.43,.08),
           (4,2.41,.05),(6,2.30,.03),(14,2.31,.05),(24,1.98,.02)]),
    (100.,[(0,3.00,.05),(1,3.15,.25),(2,2.51,.09),(3,2.52,.01),
           (4,2.33,.11),(6,2.18,.03),(14,2.01,.05),(24,1.92,.06)]),
    (120.,[(0,4.11,.16),(1,6.10,1.10),(2,6.28,.17),(3,6.46,.01),
           (4,3.26,.18),(6,3.41,.03),(14,3.15,.04),(24,3.06,.05)]),
]

PP_OUTDOOR_DIGITIZED_OBSERVATIONS = [
    {
        'source_id':'mdpi-pp-zno-sunlight-2020','experiment_id':'BANGKOK-PP-NEAT',
        'formulation':'PP vierge sans ZnO, injecté','protocol':'ASTM D638; injection; 100 mm/min; Bangkok; septembre 2018 à mars 2019; UV index 8–14; 22–39 °C',
        'uncertainty':2.0,
        'values':[(0,241),(21,285),(42,284),(84,263),(126,252),(168,244)],
    },
    {
        'source_id':'ccse-pp-riyadh-weathering-2011','experiment_id':'RIYADH-PP520L-NEAT',
        'formulation':'PP520L SABIC homopolymère sans additif, injecté','protocol':'ASTM D638; injection; 5 mm/min; Riyad; avril à septembre 2009; prélèvement tous les 2 mois',
        'uncertainty':5.0,
        'values':[(0,1400),(60.875,620),(121.75,580),(182.625,1060)],
    },
]

# Propriétés initiales de grades commerciaux. Elles servent uniquement à
# initialiser une projection de présélection : elles ne constituent pas des
# séries temporelles de vieillissement. Chaque ligne possède deux contrôles
# officiels et conserve les conditions qui rendent la valeur interprétable.
REFERENCE_PROPERTIES = [
    dict(id='PP-HP501L-E',material_id='PP',grade='Moplen HP501L',property_name='Module en traction',
         representative_mpa=1500.,minimum_mpa=1500.,maximum_mpa=1500.,test_standard='ISO 527',test_temperature_c=23.,
         conditioning='Standard, valeur typique fabricant',process='Moulage par injection',primary_source_id='lyb-moplen-hp501l',
         cross_source_id='lyb-pp-selection-guide',source_location='Page produit et guide de sélection',
         verification_status='cross_checked_official',cross_check_note='Même grade et même valeur dans deux documents officiels LyondellBasell.',screening_default=1),
    dict(id='PC-2407-E',material_id='PC',grade='Makrolon 2407',property_name='Module en traction',
         representative_mpa=2400.,minimum_mpa=2400.,maximum_mpa=2400.,test_standard='ISO 527-1/-2',test_temperature_c=23.,
         conditioning='23 °C, valeur typique fabricant',process='Moulage par injection',primary_source_id='covestro-makrolon-2407-tds',
         cross_source_id='covestro-makrolon-2407-page',source_location='Fiche ISO et page produit',
         verification_status='cross_checked_official',cross_check_note='Même grade confirmé par la fiche ISO et la page officielle Covestro.',screening_default=1),
    dict(id='ABS-GP22-E',material_id='ABS',grade='Terluran GP-22',property_name='Module en traction',
         representative_mpa=2300.,minimum_mpa=2300.,maximum_mpa=2300.,test_standard='ISO 527',test_temperature_c=23.,
         conditioning='23 °C, valeur typique fabricant',process='Moulage par injection',primary_source_id='ineos-terluran-gp22',
         cross_source_id='ineos-terluran-range',source_location='Page grade et tableau de gamme',
         verification_status='cross_checked_official',cross_check_note='Même grade et même valeur dans deux pages officielles INEOS Styrolution.',screening_default=1),
    dict(id='PBT-B4520-E',material_id='PBT',grade='Ultradur B 4520',property_name='Module en traction',
         representative_mpa=2400.,minimum_mpa=2400.,maximum_mpa=2400.,test_standard='ISO 527-1/-2',test_temperature_c=23.,
         conditioning='Sec, 23 °C, valeur typique fabricant',process='Moulage par injection',primary_source_id='basf-ultradur-b4520',
         cross_source_id='basf-ultradur-b4520-black',source_location='Fiche grade naturel et variante noire',
         verification_status='cross_checked_official',cross_check_note='Valeur identique pour le B 4520 naturel et sa variante noire officielle.',screening_default=1),
    dict(id='PA66-A3K-DRY-E',material_id='PA66',grade='Ultramid A3K / A3K R01',property_name='Module en traction',
         representative_mpa=3050.,minimum_mpa=3000.,maximum_mpa=3100.,test_standard='ISO 527-1/-2',test_temperature_c=23.,
         conditioning='À sec',process='Moulage par injection',primary_source_id='basf-ultramid-a3k',
         cross_source_id='basf-ultramid-a3k-r01',source_location='Fiches A3K et A3K R01',
         verification_status='cross_checked_official',cross_check_note='Deux révisions BASF donnent 3 000 et 3 100 MPa à sec ; le milieu de la plage est retenu.',screening_default=1),
    dict(id='PA66-A3K-COND-E',material_id='PA66',grade='Ultramid A3K / A3K R01',property_name='Module en traction',
         representative_mpa=1100.,minimum_mpa=1100.,maximum_mpa=1100.,test_standard='ISO 527-1/-2',test_temperature_c=23.,
         conditioning='Conditionné',process='Moulage par injection',primary_source_id='basf-ultramid-a3k',
         cross_source_id='basf-ultramid-a3k-r01',source_location='Fiches A3K et A3K R01',
         verification_status='cross_checked_official',cross_check_note='Les deux fiches BASF confirment 1 100 MPa après conditionnement.',screening_default=0),
    dict(id='POM-UNFILLED-E',material_id='POM',grade='Ultraform N2320 003 PRO AT / Hostaform C 9021',property_name='Module en traction',
         representative_mpa=2775.,minimum_mpa=2700.,maximum_mpa=2850.,test_standard='ISO 527',test_temperature_c=23.,
         conditioning='Standard, grades non renforcés',process='Moulage par injection',primary_source_id='basf-ultraform-n2320',
         cross_source_id='celanese-hostaform-c9021',source_location='Documents fabricants des deux grades',
         verification_status='cross_checked_official',cross_check_note='Contrôle inter-fabricants sur deux POM copolymères non renforcés ; plage, pas valeur d’un grade unique.',screening_default=1),
    dict(id='COC-6013-E',material_id='COC',grade='TOPAS 6013M-07 / famille 6013',property_name='Module en traction',
         representative_mpa=2950.,minimum_mpa=2900.,maximum_mpa=3000.,test_standard='ISO 527',test_temperature_c=23.,
         conditioning='ISO 291, 23/50',process='Moulage par injection',primary_source_id='topas-6013m07-tds',
         cross_source_id='topas-product-brochure',source_location='Fiche 6013M-07 et tableau de la famille 6013',
         verification_status='cross_checked_official',cross_check_note='La fiche en unités anglaises convertie en MPa et la brochure officielle encadrent le domaine 2 900–3 000 MPa.',screening_default=1),
    dict(id='PPSU-UNFILLED-E',material_id='PPSU',grade='TECASON P / Radel R-5000',property_name='Module en traction',
         representative_mpa=2322.,minimum_mpa=2300.,maximum_mpa=2344.,test_standard='ISO 527-2 / ASTM D638',test_temperature_c=23.,
         conditioning='Standard, grades PPSU non renforcés',process='Forme semi-finie / injection',primary_source_id='ensinger-tecason-p',
         cross_source_id='syensqo-radel-design',source_location='Fiche Ensinger et guide Syensqo',
         verification_status='cross_checked_official',cross_check_note='Deux fabricants et deux normes donnent des valeurs proches ; domaine indicatif de famille, pas équivalence de grades.',screening_default=1),
    dict(id='PA11-DRY-E',material_id='PA11',grade='Rilsan KNO T3L',property_name='Module en traction',
         representative_mpa=1300.,minimum_mpa=1300.,maximum_mpa=1300.,test_standard='ISO 527-1/-2',test_temperature_c=23.,
         conditioning='À sec',process='Moulage par injection',primary_source_id='arkema-rilsan-kno-t3l',
         cross_source_id='arkema-rilsan-kno-t3l-ja',source_location='Fiches officielles anglaise et japonaise du KNO T3L',
         verification_status='cross_checked_official',cross_check_note='Les deux éditions officielles du même grade confirment 1 300 MPa à sec.',screening_default=1),
    dict(id='PA11-COND-E',material_id='PA11',grade='Rilsan KNO T3L',property_name='Module en traction',
         representative_mpa=1100.,minimum_mpa=1100.,maximum_mpa=1100.,test_standard='ISO 527',test_temperature_c=23.,
         conditioning='Conditionné',process='Moulage par injection',primary_source_id='arkema-rilsan-kno-t3l',
         cross_source_id='arkema-rilsan-kno-t3l-ja',source_location='Fiches officielles anglaise et japonaise du KNO T3L',
         verification_status='cross_checked_official',cross_check_note='Les deux éditions officielles du même grade confirment 1 100 MPa après conditionnement.',screening_default=0),
    dict(id='COP-480R-E',material_id='COP',grade='ZEONEX 480R',property_name='Module en traction',
         representative_mpa=2100.,minimum_mpa=2100.,maximum_mpa=2100.,test_standard='ISO 527',test_temperature_c=23.,
         conditioning='Standard, valeur typique fabricant',process='Moulage par injection',primary_source_id='zeon-cop-properties-en',
         cross_source_id='zeon-cop-properties-cn',source_location='Tableaux officiels anglais et chinois',
         verification_status='cross_checked_official',cross_check_note='Même grade et même valeur dans deux éditions linguistiques officielles Zeon.',screening_default=1),
]

READINESS = {
    "taxonomy_only": ("Fiche documentaire", "Identité et mécanismes seulement"),
    "source_identified": ("Sources identifiées", "Des travaux pertinents existent ; séries numériques absentes"),
    "candidate_literature": ("Publication candidate", "Source scientifique à extraire et valider"),
    "data_pending_review": ("Données à valider", "Mesures importées mais non approuvées"),
    "verified_datasheet": ("Fiche technique recoupée", "Module initial confirmé par deux documents officiels ; cinétique non mesurée"),
    "published_evidence": ("Mesures publiées vérifiées", "Valeurs exactes exploitables uniquement dans le domaine observé"),
    "accepted_limited": ("Corpus accepté limité", "Interpolation possible aux conditions exactes ; corpus insuffisant pour entraîner et valider un modèle"),
    "model_ready": ("Modélisable", "Corpus minimum validé ; modèle encore à évaluer"),
    "validated": ("Validé", "Performance indépendante documentée"),
}

def migrate() -> None:
    with store.connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS material_sources (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, organization TEXT NOT NULL,
            url TEXT NOT NULL, doi TEXT, accessed TEXT NOT NULL, scope TEXT NOT NULL,
            license_note TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS materials (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, abbreviation TEXT NOT NULL,
            family TEXT NOT NULL, subtype TEXT NOT NULL, priority INTEGER NOT NULL,
            mechanisms TEXT NOT NULL, target_property TEXT NOT NULL,
            readiness TEXT NOT NULL, source_id TEXT NOT NULL, note TEXT NOT NULL,
            curated_at TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES material_sources(id)
        );
        CREATE TABLE IF NOT EXISTS material_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, material_id TEXT NOT NULL,
            experiment_id TEXT NOT NULL, time_days REAL NOT NULL,
            modulus_mpa REAL NOT NULL, ageing_temperature_c REAL NOT NULL,
            measurement_temperature_c REAL, protocol TEXT NOT NULL,
            source_id TEXT NOT NULL, source_location TEXT NOT NULL,
            review_status TEXT NOT NULL CHECK(review_status IN ('pending','accepted','rejected')),
            FOREIGN KEY(material_id) REFERENCES materials(id),
            FOREIGN KEY(source_id) REFERENCES material_sources(id),
            UNIQUE(source_id, experiment_id, time_days)
        );
        CREATE TABLE IF NOT EXISTS aging_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT, material_id TEXT NOT NULL,
            experiment_id TEXT NOT NULL, time_days REAL NOT NULL,
            modulus_mpa REAL NOT NULL, standard_deviation_mpa REAL,
            sample_count INTEGER, exposure_mode TEXT NOT NULL,
            protocol TEXT NOT NULL, source_id TEXT NOT NULL, source_location TEXT NOT NULL,
            evidence_status TEXT NOT NULL, ageing_temperature_c REAL, humidity_rh REAL,
            thickness_mm REAL, medium TEXT, property_name TEXT,
            measurement_temperature_c REAL, UNIQUE(source_id,experiment_id,time_days)
        );
        CREATE TABLE IF NOT EXISTS research_candidates (
            id TEXT PRIMARY KEY, material_id TEXT NOT NULL, source_id TEXT NOT NULL,
            target_property TEXT NOT NULL, exposure TEXT NOT NULL, status TEXT NOT NULL,
            reason TEXT NOT NULL, next_action TEXT NOT NULL,
            FOREIGN KEY(material_id) REFERENCES materials(id),
            FOREIGN KEY(source_id) REFERENCES material_sources(id)
        );
        CREATE TABLE IF NOT EXISTS material_reference_properties (
            id TEXT PRIMARY KEY, material_id TEXT NOT NULL, grade TEXT NOT NULL,
            property_name TEXT NOT NULL, representative_mpa REAL NOT NULL CHECK(representative_mpa>0),
            minimum_mpa REAL NOT NULL CHECK(minimum_mpa>0),
            maximum_mpa REAL NOT NULL CHECK(maximum_mpa>=minimum_mpa),
            test_standard TEXT NOT NULL, test_temperature_c REAL,
            conditioning TEXT NOT NULL, process TEXT NOT NULL,
            primary_source_id TEXT NOT NULL, cross_source_id TEXT NOT NULL,
            source_location TEXT NOT NULL,
            verification_status TEXT NOT NULL CHECK(verification_status IN ('cross_checked_official','review_required')),
            cross_check_note TEXT NOT NULL,
            screening_default INTEGER NOT NULL CHECK(screening_default IN (0,1)),
            verified_at TEXT NOT NULL,
            FOREIGN KEY(material_id) REFERENCES materials(id),
            FOREIGN KEY(primary_source_id) REFERENCES material_sources(id),
            FOREIGN KEY(cross_source_id) REFERENCES material_sources(id)
        );
        CREATE INDEX IF NOT EXISTS idx_observations_material_status
            ON material_observations(material_id,review_status,experiment_id,time_days);
        CREATE INDEX IF NOT EXISTS idx_evidence_material_exposure
            ON aging_evidence(material_id,exposure_mode,experiment_id,time_days);
        CREATE INDEX IF NOT EXISTS idx_reference_properties_material
            ON material_reference_properties(material_id,screening_default);
        """)
        existing={row['name'] for row in conn.execute('PRAGMA table_info(material_observations)')}
        for name,kind in {
            'time_hours':'REAL','initial_modulus_mpa':'REAL','residual_property':'REAL',
            'humidity_rh':'REAL','thickness_mm':'REAL','reviewer':'TEXT',
            'review_note':'TEXT','reviewed_at':'TEXT','extraction_method':'TEXT',
            'extraction_uncertainty_pct':'REAL',
        }.items():
            if name not in existing:
                conn.execute(f'ALTER TABLE material_observations ADD COLUMN {name} {kind}')
        observation_info={row['name']:row for row in conn.execute('PRAGMA table_info(material_observations)')}
        if observation_info['measurement_temperature_c']['notnull']:
            conn.executescript("""
            CREATE TABLE material_observations_v3 (
                id INTEGER PRIMARY KEY AUTOINCREMENT, material_id TEXT NOT NULL,
                experiment_id TEXT NOT NULL, time_days REAL NOT NULL,
                modulus_mpa REAL NOT NULL, ageing_temperature_c REAL NOT NULL,
                measurement_temperature_c REAL, protocol TEXT NOT NULL,
                source_id TEXT NOT NULL, source_location TEXT NOT NULL,
                review_status TEXT NOT NULL CHECK(review_status IN ('pending','accepted','rejected')),
                time_hours REAL, initial_modulus_mpa REAL, residual_property REAL,
                humidity_rh REAL, thickness_mm REAL, reviewer TEXT, review_note TEXT,
                reviewed_at TEXT, extraction_method TEXT, extraction_uncertainty_pct REAL,
                FOREIGN KEY(material_id) REFERENCES materials(id),
                FOREIGN KEY(source_id) REFERENCES material_sources(id),
                UNIQUE(source_id, experiment_id, time_days)
            );
            INSERT INTO material_observations_v3
                SELECT id,material_id,experiment_id,time_days,modulus_mpa,ageing_temperature_c,
                    measurement_temperature_c,protocol,source_id,source_location,review_status,
                    time_hours,initial_modulus_mpa,residual_property,humidity_rh,thickness_mm,
                    reviewer,review_note,reviewed_at,extraction_method,extraction_uncertainty_pct
                FROM material_observations;
            DROP TABLE material_observations;
            ALTER TABLE material_observations_v3 RENAME TO material_observations;
            CREATE INDEX idx_observations_material_status
                ON material_observations(material_id,review_status,experiment_id,time_days);
            """)
        evidence_columns={row['name'] for row in conn.execute('PRAGMA table_info(aging_evidence)')}
        for name,kind in {
            'reviewer':'TEXT','review_note':'TEXT','reviewed_at':'TEXT','license_note':'TEXT',
            'ageing_temperature_c':'REAL','humidity_rh':'REAL','thickness_mm':'REAL',
            'medium':'TEXT','property_name':'TEXT','measurement_temperature_c':'REAL',
            'extraction_method':'TEXT','extraction_uncertainty_pct':'REAL',
            'formulation':'TEXT'
        }.items():
            if name not in evidence_columns:
                conn.execute(f'ALTER TABLE aging_evidence ADD COLUMN {name} {kind}')
        material_columns={row['name'] for row in conn.execute('PRAGMA table_info(materials)')}
        for name in ('category','subcategory','evidence_status','taxonomy_source_id'):
            if name not in material_columns:
                conn.execute(f'ALTER TABLE materials ADD COLUMN {name} TEXT')
        for source in SOURCES:
            conn.execute("""INSERT INTO material_sources
                (id,title,organization,url,doi,accessed,scope,license_note)
                VALUES (:id,:title,:organization,:url,:doi,:accessed,:scope,:license_note)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title, organization=excluded.organization,
                url=excluded.url, doi=excluded.doi, accessed=excluded.accessed,
                scope=excluded.scope, license_note=excluded.license_note""", source)
        today=date.today().isoformat()
        for material in MATERIALS:
            category,subcategory,evidence=classification(material)
            conn.execute("""INSERT INTO materials
                (id,name,abbreviation,family,subtype,priority,mechanisms,target_property,readiness,source_id,note,curated_at)
                VALUES (:id,:name,:abbreviation,:family,:subtype,:priority,:mechanisms,:target_property,:readiness,:source_id,:note,:curated_at)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, abbreviation=excluded.abbreviation,
                family=excluded.family, subtype=excluded.subtype, priority=excluded.priority,
                mechanisms=excluded.mechanisms, target_property=excluded.target_property,
                readiness=excluded.readiness, source_id=excluded.source_id,
                note=excluded.note, curated_at=excluded.curated_at""", material | {"curated_at": today})
            conn.execute("""UPDATE materials SET category=?,subcategory=?,evidence_status=?,taxonomy_source_id=? WHERE id=?""",
                (category,subcategory,evidence,'nims-taxonomy',material['id']))
        for reference in REFERENCE_PROPERTIES:
            conn.execute("""INSERT INTO material_reference_properties
                (id,material_id,grade,property_name,representative_mpa,minimum_mpa,maximum_mpa,
                 test_standard,test_temperature_c,conditioning,process,primary_source_id,cross_source_id,
                 source_location,verification_status,cross_check_note,screening_default,verified_at)
                VALUES (:id,:material_id,:grade,:property_name,:representative_mpa,:minimum_mpa,:maximum_mpa,
                 :test_standard,:test_temperature_c,:conditioning,:process,:primary_source_id,:cross_source_id,
                 :source_location,:verification_status,:cross_check_note,:screening_default,:verified_at)
                ON CONFLICT(id) DO UPDATE SET material_id=excluded.material_id,grade=excluded.grade,
                 property_name=excluded.property_name,representative_mpa=excluded.representative_mpa,
                 minimum_mpa=excluded.minimum_mpa,maximum_mpa=excluded.maximum_mpa,
                 test_standard=excluded.test_standard,test_temperature_c=excluded.test_temperature_c,
                 conditioning=excluded.conditioning,process=excluded.process,
                 primary_source_id=excluded.primary_source_id,cross_source_id=excluded.cross_source_id,
                 source_location=excluded.source_location,verification_status=excluded.verification_status,
                 cross_check_note=excluded.cross_check_note,screening_default=excluded.screening_default,
                 verified_at=excluded.verified_at""", reference | {'verified_at':today})
        for candidate in RESEARCH_CANDIDATES:
            conn.execute("""INSERT INTO research_candidates
                (id,material_id,source_id,target_property,exposure,status,reason,next_action)
                VALUES (:id,:material_id,:source_id,:target_property,:exposure,:status,:reason,:next_action)
                ON CONFLICT(id) DO UPDATE SET material_id=excluded.material_id,
                source_id=excluded.source_id,target_property=excluded.target_property,
                exposure=excluded.exposure,status=excluded.status,reason=excluded.reason,
                next_action=excluded.next_action""", candidate)
        for experiment in CANDIDATE_OBSERVATIONS:
            for days,modulus in experiment['values']:
                conn.execute("""INSERT OR IGNORE INTO material_observations
                    (material_id,experiment_id,time_days,modulus_mpa,ageing_temperature_c,
                     measurement_temperature_c,protocol,source_id,source_location,review_status,
                     time_hours,initial_modulus_mpa,residual_property,humidity_rh,thickness_mm,
                     extraction_method,extraction_uncertainty_pct)
                    VALUES ('FLAX_EPOXY',?,?,?,?,NULL,'ASTM D3039; room temperature (exact value not reported); 2 mm/min; n=5','scida-2013-flax-epoxy',?,'pending',?,?,?,?,?,'figure_digitization',3.0)""",
                    (experiment['experiment_id'],days,modulus,experiment['temperature_C'],
                     f'Figure 4a, t={days} jours',days*24,26600.,modulus/26600.,
                     experiment['humidity_RH'],experiment['thickness_mm']))
        for experiment_id, values in MDPI_PP_OBSERVATIONS:
            formulation=('PP H301 Braskem; 1 extrusion; injection Type I' if experiment_id=='MDPI-RPP1X' else
                         'PP H301 Braskem; 3 extrusions; injection Type I' if experiment_id=='MDPI-RPP3X' else
                         'PP H301 Braskem; 3 extrusions; 3 wt% corn husk fiber; injection Type I' if experiment_id=='MDPI-RPP3X-3CHF' else
                         'PP H301 Braskem; 3 extrusions; 5 wt% corn husk fiber; injection Type I')
            for days,modulus,sd in values:
                conn.execute("""INSERT OR IGNORE INTO aging_evidence
                    (material_id,experiment_id,time_days,modulus_mpa,standard_deviation_mpa,
                     sample_count,exposure_mode,protocol,source_id,source_location,evidence_status)
                    VALUES ('PP',?,?,?,?,7,'outdoor',?,
                            'mdpi-pp-natural-aging-2024',?,'source_verified_table')""",
                    (experiment_id,days,modulus,sd,formulation+'; ASTM D638; 50 mm/min; room temperature; n=7',
                     f'Tableau 2, {experiment_id}, t={days} jours'))
        for ageing_temperature, values in MDPI_IIR_MWF_OBSERVATIONS:
            experiment_id=f'IIR-MWF-{int(ageing_temperature)}C'
            for hours,modulus,sd in values:
                conn.execute("""INSERT OR IGNORE INTO aging_evidence
                    (material_id,experiment_id,time_days,modulus_mpa,standard_deviation_mpa,
                     sample_count,exposure_mode,protocol,source_id,source_location,evidence_status,
                     ageing_temperature_c,medium,property_name,extraction_method,formulation)
                    VALUES ('IIR',?,?,?,?,NULL,'immersion',?,
                            'mdpi-iir-mwf-2019',?,'source_verified_table',?,
                            'Milform 64 SST','Module de Young en traction','direct_table_transcription',
                            'Composite de caoutchouc butyle chargé de noir de carbone')""",
                    (experiment_id,hours/24,modulus,sd,
                     'Immersion Milform 64 SST; traction; haute température; formulation BRC de l’article',
                     f'Tableau 2, E exp, {ageing_temperature:g} °C, t={hours:g} h',ageing_temperature))
        for experiment in PP_OUTDOOR_DIGITIZED_OBSERVATIONS:
            for days,modulus in experiment['values']:
                figure='Figure 4' if experiment['source_id']=='mdpi-pp-zno-sunlight-2020' else 'Figure 8'
                conn.execute("""INSERT OR IGNORE INTO aging_evidence
                    (material_id,experiment_id,time_days,modulus_mpa,standard_deviation_mpa,
                     sample_count,exposure_mode,protocol,source_id,source_location,evidence_status,
                     medium,property_name,extraction_method,extraction_uncertainty_pct,formulation)
                    VALUES ('PP',?,?,?,?,NULL,'outdoor',?,?,?,?,
                            'air extérieur, soleil naturel','Module de Young en traction',
                            'controlled_figure_digitization',?,?)""",
                    (experiment['experiment_id'],days,modulus,None,experiment['protocol'],
                     experiment['source_id'],f'{figure}, t={days:g} jours','source_verified_table',
                     experiment['uncertainty'],experiment['formulation']))
        conn.execute("""UPDATE aging_evidence SET protocol=CASE experiment_id
            WHEN 'MDPI-RPP1X' THEN 'PP H301 Braskem; 1 extrusion; injection Type I; ASTM D638; 50 mm/min; room temperature; n=7'
            WHEN 'MDPI-RPP3X' THEN 'PP H301 Braskem; 3 extrusions; injection Type I; ASTM D638; 50 mm/min; room temperature; n=7'
            WHEN 'MDPI-RPP3X-3CHF' THEN 'PP H301 Braskem; 3 extrusions; 3 wt% corn husk fiber; injection Type I; ASTM D638; 50 mm/min; room temperature; n=7'
            WHEN 'MDPI-RPP3X-5CHF' THEN 'PP H301 Braskem; 3 extrusions; 5 wt% corn husk fiber; injection Type I; ASTM D638; 50 mm/min; room temperature; n=7'
            ELSE protocol END WHERE source_id='mdpi-pp-natural-aging-2024'""")
        conn.execute("""UPDATE material_observations SET measurement_temperature_c=NULL,
            protocol='ASTM D3039; room temperature (exact value not reported); 2 mm/min; n=5'
            WHERE source_id='scida-2013-flax-epoxy'""")
        conn.execute("""UPDATE aging_evidence SET evidence_status='source_verified_table',
            reviewer=COALESCE(reviewer,'Materia source audit 2026-09-29'),
            review_note=COALESCE(review_note,'Primary open-access article and Table 2 checked; means, standard deviations, sample count, formulations and exposure times matched.'),
            reviewed_at=COALESCE(reviewed_at,'2026-09-29T00:00:00+00:00'),
            license_note=COALESCE(license_note,'CC BY 4.0')
            WHERE source_id='mdpi-pp-natural-aging-2024'
              AND experiment_id IN ('MDPI-RPP1X','MDPI-RPP3X','MDPI-RPP3X-3CHF','MDPI-RPP3X-5CHF')""")
        conn.execute("""UPDATE aging_evidence SET property_name='Module de Young en traction',
            medium='air extérieur, climat naturel',measurement_temperature_c=COALESCE(measurement_temperature_c,23),
            extraction_method=COALESCE(extraction_method,'direct_table_transcription'),
            formulation=COALESCE(formulation,protocol)
            WHERE source_id='mdpi-pp-natural-aging-2024'
              AND experiment_id IN ('MDPI-RPP1X','MDPI-RPP3X','MDPI-RPP3X-3CHF','MDPI-RPP3X-5CHF')""")
        conn.commit()

def catalog() -> list[dict]:
    migrate()
    with store.connect() as conn:
        rows=conn.execute("""SELECT m.*, s.title source_title, s.organization,
            s.url source_url, s.doi source_doi, s.scope source_scope,
            (SELECT COUNT(*) FROM material_observations o WHERE o.material_id=m.id AND o.review_status='accepted') accepted_observations,
            (SELECT COUNT(DISTINCT o.experiment_id) FROM material_observations o WHERE o.material_id=m.id AND o.review_status='accepted') accepted_experiments,
            (SELECT COUNT(*) FROM material_observations o WHERE o.material_id=m.id AND o.review_status='pending') pending_observations
            ,(SELECT COUNT(*) FROM aging_evidence e WHERE e.material_id=m.id AND e.evidence_status='source_verified_table') verified_evidence_observations
            ,(SELECT COUNT(DISTINCT e.experiment_id) FROM aging_evidence e WHERE e.material_id=m.id AND e.evidence_status='source_verified_table') verified_evidence_experiments
            ,(SELECT COUNT(*) FROM material_reference_properties p WHERE p.material_id=m.id AND p.verification_status='cross_checked_official') verified_reference_properties
            FROM materials m JOIN material_sources s ON s.id=m.source_id
            ORDER BY m.category, m.subcategory, m.name""").fetchall()
    result = [dict(r) for r in rows]
    for item in result:
        if item["accepted_observations"] >= 12 and item["accepted_experiments"] >= 3:
            item["readiness"] = "model_ready"
        elif item["accepted_observations"]:
            item["readiness"] = "accepted_limited"
            item["evidence_status"] = "experimental_accepted_limited"
        elif item["pending_observations"] and item["readiness"] not in {"model_ready", "validated"}:
            item["readiness"] = "data_pending_review"
        elif item["verified_evidence_observations"]:
            item["readiness"] = "published_evidence"
            item["evidence_status"] = "published_table_verified"
        elif item["verified_reference_properties"]:
            item["readiness"] = "verified_datasheet"
            item["evidence_status"] = "datasheet_cross_checked"
    return result

def reference_properties(material_id: str) -> list[dict]:
    """Return traceable initial-property records, never ageing observations."""
    migrate()
    with store.connect() as conn:
        rows=conn.execute("""SELECT p.*,
            a.title primary_source_title,a.organization primary_organization,a.url primary_source_url,
            b.title cross_source_title,b.organization cross_organization,b.url cross_source_url
            FROM material_reference_properties p
            JOIN material_sources a ON a.id=p.primary_source_id
            JOIN material_sources b ON b.id=p.cross_source_id
            WHERE p.material_id=? ORDER BY p.screening_default DESC,p.conditioning,p.grade""",
            (material_id,)).fetchall()
    return [dict(row) for row in rows]

def reference_property_profile(material_id: str) -> dict | None:
    """Return the reviewed default grade profile for screening simulations."""
    rows=[row for row in reference_properties(material_id)
          if row['verification_status']=='cross_checked_official' and row['screening_default']]
    if not rows:
        return None
    # The curated dataset currently has one default record per material. Keeping
    # this aggregation deterministic also protects a later multi-grade extension.
    representative=sum(float(row['representative_mpa']) for row in rows)/len(rows)
    return {
        'representative_mpa':representative,
        'minimum_mpa':min(float(row['minimum_mpa']) for row in rows),
        'maximum_mpa':max(float(row['maximum_mpa']) for row in rows),
        'grade':' / '.join(row['grade'] for row in rows),
        'test_standard':' / '.join(dict.fromkeys(row['test_standard'] for row in rows)),
        'conditioning':' / '.join(dict.fromkeys(row['conditioning'] for row in rows)),
        'source_ids':[source for row in rows for source in (row['primary_source_id'],row['cross_source_id'])],
        'source_titles':[source for row in rows for source in (row['primary_source_title'],row['cross_source_title'])],
        'verification_status':'cross_checked_official',
        'record_ids':[row['id'] for row in rows],
    }

def propose_observations(material_id: str, rows: list[dict], source_url: str) -> dict:
    """Place imported measurements in the review queue without approving them."""
    migrate()
    if not material(material_id):
        raise ValueError("Matériau cible inconnu.")
    if not source_url.startswith("https://"):
        raise ValueError("Une URL HTTPS vers la source scientifique est obligatoire.")
    if not rows:
        raise ValueError("Aucune mesure à proposer.")
    source_id = "import-" + hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]
    source_title = str(rows[0].get("source") or "Source déclarée par l’importateur")[:300]
    inserted = 0
    with store.connect() as conn:
        conn.execute("""INSERT INTO material_sources
            (id,title,organization,url,doi,accessed,scope,license_note)
            VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING""",
            (source_id, source_title, "Source déclarée par l’importateur", source_url, None,
             date.today().isoformat(), "Mesures proposées depuis un jeu CSV utilisateur.",
             "Licence, méthode et fidélité de l’extraction à contrôler avant acceptation."))
        for row in rows:
            cursor = conn.execute("""INSERT OR IGNORE INTO material_observations
                (material_id,experiment_id,time_days,modulus_mpa,ageing_temperature_c,
                 measurement_temperature_c,protocol,source_id,source_location,review_status,
                 time_hours,initial_modulus_mpa,residual_property,humidity_rh,thickness_mm)
                VALUES (?,?,?,?,?,?,?,?,?,'pending',?,?,?,?,?)""",
                (material_id, row["experiment_id"], row["time_days"], row["modulus_MPa"],
                 row["temperature_C"], row["measurement_temperature_C"], row["protocol"],
                 source_id, row["location"], row.get('time_hours'), row.get('initial_modulus_MPa'),
                 row.get('residual_property'), row.get('humidity_RH'), row.get('thickness_mm')))
            inserted += cursor.rowcount
        conn.commit()
    return {"inserted": inserted, "duplicates": len(rows) - inserted,
            "source_id": source_id, "status": "pending"}

def review_batches(status: str = 'pending') -> list[dict]:
    migrate()
    if status not in {'pending','accepted','rejected'}:
        raise ValueError('Statut de revue inconnu.')
    with store.connect() as conn:
        rows=conn.execute("""SELECT o.material_id,o.source_id,o.experiment_id,o.review_status,
            COUNT(*) observation_count,COUNT(DISTINCT o.time_days) distinct_times,
            MIN(o.time_hours) min_time_hours,MAX(o.time_hours) max_time_hours,
            MIN(o.ageing_temperature_c) temperature_c,MIN(o.humidity_rh) humidity_rh,
            MIN(o.thickness_mm) thickness_mm,s.title source_title,s.url source_url,
            MIN(o.source_location) first_location,MAX(o.reviewer) reviewer,
            MAX(o.review_note) review_note,MAX(o.reviewed_at) reviewed_at,
            MAX(o.extraction_method) extraction_method,
            MAX(o.extraction_uncertainty_pct) extraction_uncertainty_pct
            FROM material_observations o JOIN material_sources s ON s.id=o.source_id
            WHERE o.review_status=? GROUP BY o.material_id,o.source_id,o.experiment_id,o.review_status
            ORDER BY s.title,o.experiment_id""",(status,)).fetchall()
    return [dict(r) for r in rows]

def batch_rows(source_id: str, experiment_id: str) -> list[dict]:
    migrate()
    with store.connect() as conn:
        rows=conn.execute("""SELECT time_hours,modulus_mpa AS modulus_MPa,
            initial_modulus_mpa AS initial_modulus_MPa,residual_property,
            ageing_temperature_c AS temperature_C,humidity_rh AS humidity_RH,
            thickness_mm,source_location AS location,review_status
            FROM material_observations WHERE source_id=? AND experiment_id=? ORDER BY time_days""",
            (source_id,experiment_id)).fetchall()
    return [dict(r) for r in rows]

def review_batch(source_id: str, experiment_id: str, decision: str, reviewer: str,
                 note: str, checks: dict[str,bool], authorized: bool = False) -> int:
    """Review one complete experiment; acceptance requires explicit traceability checks."""
    if not authorized:
        raise PermissionError('Une autorisation de validateur scientifique est requise.')
    if decision not in {'accepted','rejected'}:
        raise ValueError('Décision de revue invalide.')
    if len(reviewer.strip()) < 3:
        raise ValueError('Indiquez le nom ou l’identifiant du relecteur.')
    if len(note.strip()) < 10:
        raise ValueError('Documentez la justification de la décision (10 caractères minimum).')
    required={'source_verified','conditions_verified','units_verified','extraction_verified'}
    if decision == 'accepted' and not all(checks.get(k) for k in required):
        raise ValueError('Tous les contrôles doivent être confirmés avant acceptation.')
    migrate()
    with store.connect() as conn:
        rows=conn.execute("""SELECT * FROM material_observations
            WHERE source_id=? AND experiment_id=? AND review_status='pending'""",
            (source_id,experiment_id)).fetchall()
        if not rows: raise ValueError('Ce lot n’est plus en attente.')
        if decision == 'accepted':
            fields=('time_hours','initial_modulus_mpa','residual_property','humidity_rh','thickness_mm')
            if any(row[field] is None for row in rows for field in fields):
                raise ValueError('Lot ancien ou incomplet : les variables hygrothermiques sont obligatoires.')
            if len({row['time_days'] for row in rows}) < 3:
                raise ValueError('Une expérience acceptée doit contenir au moins trois temps distincts.')
        now=datetime.now(timezone.utc).isoformat()
        cursor=conn.execute("""UPDATE material_observations SET review_status=?,reviewer=?,
            review_note=?,reviewed_at=? WHERE source_id=? AND experiment_id=? AND review_status='pending'""",
            (decision,reviewer.strip(),note.strip(),now,source_id,experiment_id))
        conn.commit()
    return cursor.rowcount

def accepted_rows(material_id: str) -> list[dict]:
    migrate()
    with store.connect() as conn:
        rows=conn.execute("""SELECT experiment_id,time_hours,time_days,modulus_mpa AS modulus_MPa,
            initial_modulus_mpa AS initial_modulus_MPa,residual_property,
            ageing_temperature_c AS temperature_C,humidity_rh AS humidity_RH,
            thickness_mm,measurement_temperature_c AS measurement_temperature_C,
            protocol,source_location AS location FROM material_observations
            WHERE material_id=? AND review_status='accepted' ORDER BY experiment_id,time_days""",
            (material_id,)).fetchall()
    return [dict(r) for r in rows]

def observation_rows(material_id: str, include_pending: bool = False) -> list[dict]:
    """Return model-shaped observations; pending rows are opt-in for review previews only."""
    migrate()
    statuses=('accepted','pending') if include_pending else ('accepted',)
    placeholders=','.join('?' for _ in statuses)
    with store.connect() as conn:
        rows=conn.execute(f"""SELECT o.experiment_id,o.time_hours,o.time_days,
            o.modulus_mpa AS modulus_MPa,o.initial_modulus_mpa AS initial_modulus_MPa,
            o.residual_property,o.ageing_temperature_c AS temperature_C,
            o.humidity_rh AS humidity_RH,o.thickness_mm,o.measurement_temperature_c AS measurement_temperature_C,
            o.review_status,o.extraction_uncertainty_pct,o.protocol,o.source_id,o.source_location,
            s.title AS source_title,s.url AS source_url,s.doi AS source_doi
            FROM material_observations o JOIN material_sources s ON s.id=o.source_id
            WHERE o.material_id=? AND o.review_status IN ({placeholders}) ORDER BY o.experiment_id,o.time_days""",
            (material_id,*statuses)).fetchall()
    return [dict(r) for r in rows]

def evidence_rows(material_id: str, exposure_mode: str | None = None) -> list[dict]:
    """Return only evidence that passed the source/table verification gate."""
    migrate()
    query="""SELECT e.*,s.title source_title,s.url source_url,s.doi source_doi
        FROM aging_evidence e JOIN material_sources s ON s.id=e.source_id
        WHERE e.material_id=? AND e.evidence_status='source_verified_table'"""
    args=[material_id]
    if exposure_mode:
        query+=' AND e.exposure_mode=?'; args.append(exposure_mode)
    query+=' ORDER BY e.experiment_id,e.time_days'
    with store.connect() as conn:
        return [dict(r) for r in conn.execute(query,args).fetchall()]

def source(source_id: str) -> dict | None:
    migrate()
    with store.connect() as conn:
        row=conn.execute('SELECT * FROM material_sources WHERE id=?',(source_id,)).fetchone()
    return dict(row) if row else None

def research_candidates(material_id: str | None = None) -> list[dict]:
    """Return qualified literature leads without promoting them to numerical evidence."""
    migrate()
    query="""SELECT c.*,s.title source_title,s.url source_url,s.doi source_doi,
        s.license_note FROM research_candidates c
        JOIN material_sources s ON s.id=c.source_id"""
    args=[]
    if material_id:
        query+=' WHERE c.material_id=?'; args.append(material_id)
    query+=' ORDER BY c.material_id,c.id'
    with store.connect() as conn:
        return [dict(r) for r in conn.execute(query,args).fetchall()]

def material(material_id: str) -> dict | None:
    return next((m for m in catalog() if m["id"] == material_id), None)

def domain_decision(material_id: str) -> dict:
    item=material(material_id)
    if not item:
        return dict(status="insufficient", label="Matériau inconnu", reason="Aucune fiche matérielle n'existe.", can_predict=False)
    if item["readiness"] == "validated":
        return dict(status="validated", label="Domaine validé", reason="Un modèle et son test indépendant sont publiés.", can_predict=True)
    if item["readiness"] == "model_ready":
        return dict(status="exploratory", label="Modèle à évaluer", reason="Les données existent mais la performance indépendante reste à établir.", can_predict=False)
    if item["readiness"] == "published_evidence":
        return dict(status="published", label="Mesures publiées exploitables", reason="Interpolation autorisée entre les temps mesurés ; aucune extrapolation de durée de vie.", can_predict=False)
    if item["readiness"] == "accepted_limited":
        return dict(status="accepted_limited", label="Corpus accepté mais limité", reason="Interpolation autorisée aux conditions exactes ; il manque une campagne indépendante pour prédire.", can_predict=False)
    if item["readiness"] == "verified_datasheet":
        return dict(status="insufficient", label="Module initial recoupé", reason="Le point de départ est relié à deux documents officiels ; la vitesse de vieillissement reste une estimation de famille.", can_predict=False)
    return dict(status="insufficient", label="Données insuffisantes", reason="Le catalogue contient une fiche et des sources, mais aucune série expérimentale acceptée permettant une durée fiable.", can_predict=False)

def corpus_audit(material_id: str) -> dict:
    """Explain the scientific gate and the shortest honest path to a model evaluation."""
    item=material(material_id)
    if not item:
        return {'material_id':material_id,'status':'unknown','trainable':False,
                'blockers':['Matériau absent du catalogue.'],'recommendations':[]}
    points=int(item['accepted_observations']); experiments=int(item['accepted_experiments'])
    published=int(item['verified_evidence_observations']); series=int(item['verified_evidence_experiments'])
    min_points,min_experiments=12,3
    blockers=[]
    if points<min_points: blockers.append(f'Il manque {min_points-points} point(s) accepté(s) pour atteindre le seuil logiciel de {min_points}.')
    if experiments<min_experiments: blockers.append(f'Il manque {min_experiments-experiments} expérience(s) indépendante(s) pour une validation par groupes.')
    if published and not points:
        blockers.append('Les valeurs publiées restent descriptives : les covariables environnementales ne permettent pas de les convertir en corpus hygrothermique.')
    if material_id=='FLAX_EPOXY':
        recommendations=[
            'Réaliser une troisième campagne indépendante à 30 °C, 90 % HR et 2,5 mm, avec les temps 0, 1, 3, 9 et 38 jours.',
            'Utiliser au moins cinq éprouvettes par temps, ASTM D3039, et enregistrer la température exacte de l’essai de traction.',
            'Conserver les répétitions brutes, moyenne, écart-type, lot matière et métadonnées afin de calculer une incertitude expérimentale.',
        ]
    elif material_id=='PP':
        recommendations=[
            'Garder les quatre formulations publiées séparées : elles ne constituent pas quatre répétitions du même matériau.',
            'Documenter température, humidité, rayonnement UV, grade, additifs et procédé pour chaque nouvelle campagne.',
            'Numériser la figure PP/Opoka dans une file de revue distincte avant toute utilisation numérique.',
        ]
    else:
        recommendations=[
            'Choisir un grade et une formulation précis, puis acquérir au moins trois campagnes indépendantes et douze points au total.',
            'Mesurer E₀ et E(t) avec un protocole constant et conserver les conditions d’exposition, le nombre d’éprouvettes et la dispersion.',
        ]
    uncertainty={
        'published_standard_deviation': published if material_id=='PP' else 0,
        'digitization_only': points if material_id=='FLAX_EPOXY' else 0,
        'predictive_interval_validated': False,
        'note': ('Les barres PP sont des écarts-types publiés ; elles décrivent la dispersion des éprouvettes.'
                 if material_id=='PP' else
                 ('La bande lin/époxy représente seulement l’incertitude de lecture estimée de la figure, pas la variabilité totale.'
                  if material_id=='FLAX_EPOXY' else 'Aucune incertitude expérimentale n’est disponible.')),
    }
    return {
        'material_id':material_id,'material_name':item['name'],'status':item['readiness'],
        'accepted_points':points,'accepted_experiments':experiments,
        'verified_published_values':published,'verified_published_series':series,
        'minimum_gate':{'points':min_points,'experiments':min_experiments},
        'missing':{'points':max(0,min_points-points),'experiments':max(0,min_experiments-experiments)},
        'trainable':points>=min_points and experiments>=min_experiments,
        'lifetime_validated':item['readiness']=='validated','blockers':blockers,
        'recommendations':recommendations,'uncertainty':uncertainty,
        'candidate_sources':research_candidates(material_id),
    }
