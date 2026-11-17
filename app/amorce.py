"""Premier contenu de la plateforme : les connecteurs publiés par SOTECHDI
(code réel, dépôts publics) et des besoins réels qu'elle n'a pas encore couverts.

Ne s'exécute que sur une base vide. Le compte est créé sans mot de passe
utilisable, sauf si MFA_AMORCE_EMAIL et MFA_AMORCE_MDP sont définis.
"""
import os

from sqlalchemy import func, select

from .db import Connecteur, Demande, Dev, Soutien, session
from .etat import relever_github
from .securite import hacher

PROPRIO_GITHUB = os.environ.get("MFA_AMORCE_GITHUB", "dondirechristian")

CONNECTEURS = [
    {
        "slug": "brvm-mcp", "nom": "brvm-mcp", "type": "mcp", "langage": "Python",
        "categorie": "finance", "service": "BRVM, Bourse régionale des valeurs mobilières (UEMOA)",
        "pays": ["BJ", "BF", "CI", "GW", "ML", "NE", "SN", "TG"],
        "resume": "Serveur MCP qui donne aux assistants IA les données publiques de la BRVM : "
                  "cours, indices, dividendes, volumes, fondamentaux et indices sectoriels.",
        "description": """La BRVM, bourse commune aux huit pays de l'UEMOA, ne publie aucune API. Ce serveur agrège **4 sources** (brvm.org, AFX Kwayisi, Rich Bourse, Sika Finance) en **18 outils MCP** : un assistant IA peut répondre à « quelles valeurs de la BRVM ont le meilleur rendement du dividende ? » avec des données du jour.

**Ce qu'il couvre**

| Domaine | Outils |
|---|---|
| Marché | résumé de séance (BRVM-C, BRVM-30, Prestige), cours des 47 valeurs, OHLC |
| Sociétés | liste par pays, fiche et documents (rapports annuels, BOC) |
| Dividendes | prochains paiements, rendement classé, recoupement Sika Finance |
| Analyse | PER, BPA, capitalisation, volumes, indices sectoriels, historique |

**Le garde-fou réglementaire.** Conseiller en investissement est une activité réglementée par l'AMF-UMOA. Chaque réponse passe par un correcteur éditorial qui bloque le vocabulaire prescriptif (*acheter*, *vendre*, *nous recommandons*, *objectif de cours*). Une réponse fautive est **rejetée, pas réécrite en silence** : la réécrire cacherait la dérive.

**Offres** : gratuit (25 appels par jour en HTTP, illimité en local), Pro et Business avec clé d'API personnelle.""",
        "installation": "claude mcp add brvm -- uvx --from git+https://github.com/sotechdi/brvm-mcp brvm-mcp",
        "depot_url": "https://github.com/SOTECHDI/brvm-mcp",
        "doc_url": "https://sotechdi.github.io/brvm-mcp/",
        "licence": "Commerciale (SOTECHDI)",
    },
    {
        "slug": "momo-xof-mcp", "nom": "momo-xof-mcp", "type": "mcp", "langage": "Python",
        "categorie": "paiement", "service": "Mobile money UEMOA via CinetPay",
        "pays": ["BJ", "BF", "CI", "GW", "ML", "NE", "SN", "TG"],
        "resume": "Serveur MCP pour demander et suivre un paiement mobile money en XOF "
                  "(Orange Money, Moov Money, Wave) dans les huit pays de l'UEMOA.",
        "description": """Le mobile money est la façon dont l'Afrique de l'Ouest paie. Des dizaines de SDK existent (PHP, Node, Python, Flutter), mais aucun serveur MCP : un agent IA ne pouvait pas demander un paiement en XOF sans intégration sur mesure.

**Trois outils**

| Outil | Rôle |
|---|---|
| `momo_list_operators` | Opérateurs et pays pris en charge |
| `momo_initiate_payment` | Demander un paiement au portefeuille d'un client |
| `momo_check_payment_status` | Suivre ce qu'est devenue la demande |

**Quatre pièges, appris contre le vrai bac à sable**

- Un appel réussi n'est pas un paiement réussi : `accepted` veut dire que l'agrégateur a pris la demande, pas que le client a payé.
- Un paiement abandonné finit `failed`, et c'est définitif : lisez `is_final`, sinon l'agent attend pour toujours.
- Réessayer avec la même référence est sans danger : l'agrégateur refuse un doublon.
- Le préfixe d'un numéro n'identifie pas le service : Wave n'a aucune plage de numéros.

État : v0.1, bac à sable CinetPay uniquement.""",
        "installation": "pip install momo-xof-mcp\n# puis, dans la configuration de votre client MCP :\n# \"command\": \"momo-xof-mcp\", \"env\": {\"MOMO_ENV\": \"sandbox\"}",
    },
    {
        "slug": "mining-cadastre-mcp", "nom": "mining-cadastre-mcp", "type": "mcp", "langage": "Python",
        "categorie": "energie-mines", "service": "Cadastre minier du Burkina Faso (DGCM)",
        "pays": ["BF"],
        "resume": "Serveur MCP en lecture seule sur la liste officielle des titres miniers "
                  "valides du Burkina Faso : titulaire, statut, dates, provinces et communes.",
        "description": """Les titres miniers du Burkina Faso sont publics, mais publiés comme des documents, pas comme des données : un PDF trimestriel scanné, avec neuf tableaux dedans. Répondre à « quels titres détient cette société, et quand expirent-ils ? » voulait dire lire un tableau scanné à l'œil.

**Ce qu'il sait dire** : qui détient un titre, son statut, ses dates d'octroi et d'expiration, ses provinces et communes, sa catégorie. 383 titres de l'édition du 31 mars 2026.

**Ce qu'il refuse de dire** : la substance (or, manganèse…). Les listes publiées ne la donnent pas, et le serveur ne devine pas à partir d'un nom de société.

**Ce qu'il n'est pas** : une source qui fait foi. Chaque réponse porte la date d'édition, la date de lecture et l'empreinte SHA-256 du PDF source. Le texte vient d'une OCR : les valeurs douteuses sont signalées, jamais corrigées en silence.

| Outil | Rôle |
|---|---|
| `cadastre_list_jurisdictions` | Pays couverts, source, édition servie, limites |
| `cadastre_search_licences` | Recherche par société, statut, code, catégorie |
| `cadastre_get_licence` | Détail d'un titre par son code |""",
        "installation": "pip install mining-cadastre-mcp\n# client MCP : \"command\": \"mining-cadastre-mcp\"",
    },
    {
        "slug": "veille-marches-publics-bf", "nom": "Veille marchés publics BF", "type": "mcp",
        "langage": "Python", "categorie": "entreprises",
        "service": "Quotidien des marchés publics (DGCMEF, Burkina Faso)", "pays": ["BF"],
        "resume": "Ingestion des Quotidiens DGCMEF : avis d'appel d'offres et, surtout, "
                  "motifs de rejet des offres, exposés à un agent via MCP.",
        "description": """Le Quotidien des marchés publics comporte deux parties. Les agrégateurs n'exploitent que les avis ouverts et ignorent la seconde.

C'est la plus utile : la section **Résultats provisoires** dit, entreprise par entreprise, *pourquoi* chaque offre a été écartée (RCCM absent ou incompatible avec le lot, agrément manquant, attestation fiscale non fournie, chiffre d'affaires insuffisant, lettre non signée).

Ce connecteur extrait les deux, et permet à un agent de répondre à « quelles erreurs font perdre les marchés dans mon secteur ? ».

Commandes : `lister`, `ingerer <url|pdf>`, `stats`, `mcp` (serveur sur stdio).""",
        "installation": "pip install -r requirements.txt\nexport PYTHONPATH=src\npython -m mpbf mcp",
        "depot": "veille-marches-publics-bf",
    },
]

DEMANDES = [
    ("Connecteur Wave (Sénégal, Côte d'Ivoire) en direct, sans agrégateur", "paiement", ["SN", "CI"],
     "Wave a sa propre API marchande. Aujourd'hui on passe par des agrégateurs qui prennent une commission en plus. "
     "Un client ou un serveur MCP qui crée une session de paiement Wave et vérifie le statut par webhook servirait à beaucoup de boutiques."),
    ("Recherche d'entreprise par numéro RCCM / IFU au Burkina Faso", "entreprises", ["BF"],
     "Vérifier qu'un fournisseur existe et que son RCCM couvre bien son activité. Les informations existent "
     "(Maison de l'entreprise, eSintax) mais aucune API publique."),
    ("Parseur du Journal officiel du Burkina Faso", "donnees-publiques", ["BF"],
     "Décrets, nominations, arrêtés : publiés en PDF. Un extracteur qui en fait des données datées, avec la page source, "
     "aiderait les juristes, les journalistes et les agents IA."),
    ("Envoi de SMS et USSD multi-opérateurs en Afrique de l'Ouest francophone", "telecoms",
     ["BF", "CI", "SN", "ML", "BJ", "TG", "NE"],
     "Notifications de commande, codes de confirmation : chaque pays a ses passerelles et ses contraintes d'identifiant "
     "d'expéditeur. Un connecteur unique, avec la liste des pièges par pays, nous ferait gagner des semaines."),
]


def amorcer() -> None:
    s = session()
    try:
        if s.scalar(select(func.count(Connecteur.id))):
            return
        email = os.environ.get("MFA_AMORCE_EMAIL", "amorce@mcp-for-africa.invalid")
        mdp = os.environ.get("MFA_AMORCE_MDP")
        dev = s.scalar(select(Dev).where(Dev.pseudo == "sotechdi"))
        if not dev:
            dev = Dev(pseudo="sotechdi", email=email.lower(), mdp=hacher(mdp) if mdp else "!",
                      pays="BF", github=PROPRIO_GITHUB,
                      bio="SOTECHDI, Ouagadougou. Agents IA et connecteurs pour les services d'Afrique de l'Ouest.")
            s.add(dev)
            s.flush()
        for d in CONNECTEURS:
            c = Connecteur(
                slug=d["slug"], nom=d["nom"], resume=d["resume"], description=d["description"],
                installation=d["installation"], categorie=d["categorie"], type=d["type"],
                langage=d["langage"], service=d["service"], pays="," + ",".join(d["pays"]) + ",",
                depot_url=d.get("depot_url") or f"https://github.com/{PROPRIO_GITHUB}/{d.get('depot', d['slug'])}",
                doc_url=d.get("doc_url", ""), licence_declaree=d.get("licence", ""), auteur_id=dev.id)
            if os.environ.get("MFA_AMORCE_RELEVE", "1") == "1":
                relever_github(c)
            s.add(c)
        for titre, cat, pays, texte in DEMANDES:
            dm = Demande(titre=titre, categorie=cat, pays="," + ",".join(pays) + ",",
                         description=texte, auteur_id=dev.id)
            s.add(dm)
            s.flush()
            s.add(Soutien(demande_id=dm.id, dev_id=dev.id))
        s.commit()
    finally:
        s.close()
