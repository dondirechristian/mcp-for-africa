"""Données de référence : pays africains, catégories, types de connecteurs."""

# Les 54 pays africains, code ISO 3166-1 alpha-2 -> nom en français.
PAYS = {
    "DZ": "Algérie", "AO": "Angola", "BJ": "Bénin", "BW": "Botswana",
    "BF": "Burkina Faso", "BI": "Burundi", "CV": "Cap-Vert", "CM": "Cameroun",
    "CF": "Centrafrique", "KM": "Comores", "CG": "Congo",
    "CD": "RD Congo", "CI": "Côte d'Ivoire", "DJ": "Djibouti", "EG": "Égypte",
    "ER": "Érythrée", "SZ": "Eswatini", "ET": "Éthiopie", "GA": "Gabon",
    "GM": "Gambie", "GH": "Ghana", "GN": "Guinée", "GW": "Guinée-Bissau",
    "GQ": "Guinée équatoriale", "KE": "Kenya", "LS": "Lesotho", "LR": "Liberia",
    "LY": "Libye", "MG": "Madagascar", "MW": "Malawi", "ML": "Mali",
    "MA": "Maroc", "MU": "Maurice", "MR": "Mauritanie", "MZ": "Mozambique",
    "NA": "Namibie", "NE": "Niger", "NG": "Nigeria", "UG": "Ouganda",
    "RW": "Rwanda", "ST": "Sao Tomé-et-Principe", "SN": "Sénégal",
    "SC": "Seychelles", "SL": "Sierra Leone", "SO": "Somalie", "SD": "Soudan",
    "SS": "Soudan du Sud", "ZA": "Afrique du Sud", "TZ": "Tanzanie", "TD": "Tchad",
    "TG": "Togo", "TN": "Tunisie", "ZM": "Zambie", "ZW": "Zimbabwe",
}

# Regroupements pratiques pour la saisie : un connecteur mobile money XOF
# couvre souvent toute l'UEMOA d'un coup.
ZONES = {
    "UEMOA": ["BJ", "BF", "CI", "GW", "ML", "NE", "SN", "TG"],
    "CEMAC": ["CM", "CF", "CG", "GA", "GQ", "TD"],
}

PAYS_TRIES = sorted(PAYS.items(), key=lambda kv: kv[1])

CATEGORIES = {
    "paiement": "Paiement & mobile money",
    "finance": "Finance & bourse",
    "donnees-publiques": "Données publiques",
    "administration": "Administration & état civil",
    "entreprises": "Entreprises, fiscalité & marchés publics",
    "telecoms": "Télécoms, SMS & USSD",
    "logistique": "Logistique & transport",
    "agriculture": "Agriculture & météo",
    "sante": "Santé",
    "education": "Éducation",
    "energie-mines": "Énergie & mines",
    "langues": "Langues africaines",
    "autre": "Autre",
}

TYPES = {
    "mcp": "Serveur MCP (agents IA)",
    "api": "Client d'API",
    "sdk": "SDK / bibliothèque",
    "jeu-de-donnees": "Jeu de données ouvert",
    "scraper": "Extracteur de documents",
}

LANGAGES = ["Python", "JavaScript / TypeScript", "PHP", "Java / Kotlin", "Dart",
            "Go", "C#", "Ruby", "Rust", "Autre"]

# Licences refusées par le règlement CADEV, et qu'on signale sur les fiches :
# un connecteur sous copyleft fort contamine le projet qui l'embarque.
LICENCES_COPYLEFT = {"GPL-2.0", "GPL-3.0", "AGPL-3.0", "LGPL-2.1", "LGPL-3.0",
                     "GPL-2.0-only", "GPL-3.0-only", "AGPL-3.0-only",
                     "LGPL-2.1-only", "LGPL-3.0-only", "GPL-2.0-or-later",
                     "GPL-3.0-or-later", "AGPL-3.0-or-later",
                     "LGPL-2.1-or-later", "LGPL-3.0-or-later"}


def drapeau(code: str) -> str:
    """Emoji drapeau à partir du code ISO (indicateurs régionaux Unicode)."""
    code = (code or "").upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code)


def nom_pays(code: str) -> str:
    return PAYS.get((code or "").upper(), code or "")


def pays_depuis_formulaire(valeurs: list[str]) -> list[str]:
    """Normalise une liste de codes (et de zones) en codes pays valides, sans doublon."""
    codes: list[str] = []
    for v in valeurs:
        v = (v or "").strip().upper()
        for c in ZONES.get(v, [v]):
            if c in PAYS and c not in codes:
                codes.append(c)
    return codes
