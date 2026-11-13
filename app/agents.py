"""Serveur MCP de Relais : un agent IA peut chercher un connecteur africain
et savoir s'il marche encore, sans quitter la conversation.

Point d'entrée : POST /mcp (transport « streamable HTTP », sans état).
"""
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import or_, select

from . import referentiel as ref
from .db import Connecteur, Demande, Essai, session
from .etat import etat

serveur_mcp = FastMCP(
    "relais",
    instructions=("Catalogue communautaire de connecteurs vers les services africains "
                  "(mobile money, données publiques, administrations). Chaque connecteur a un "
                  "état « vivant / à vérifier / signalé cassé » tenu par la communauté."),
    stateless_http=True,
    json_response=True,
    streamable_http_path="/mcp",
    # Derrière l'hébergeur, l'en-tête Host est le domaine public : la protection
    # anti-rebinding (prévue pour les serveurs locaux) refuserait toutes les requêtes.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

def _fiche(c: Connecteur, essais: list[Essai]) -> dict:
    e = etat(c, essais)
    return {
        "slug": c.slug, "nom": c.nom, "resume": c.resume, "service": c.service,
        "categorie": ref.CATEGORIES.get(c.categorie, c.categorie),
        "type": ref.TYPES.get(c.type, c.type), "langage": c.langage,
        "pays": [ref.nom_pays(p) for p in c.codes_pays],
        "depot": c.depot_url, "licence": c.gh_licence or "inconnue",
        "etat": e["libelle"], "pourquoi": e["raisons"],
        "installation": c.installation,
    }


@serveur_mcp.tool()
def chercher_connecteurs(recherche: str = "", pays: str = "", categorie: str = "") -> list[dict]:
    """Cherche des connecteurs vers des services africains.

    recherche : mots-clés (ex. « orange money », « cadastre », « wave »).
    pays : code ISO à deux lettres (BF, CI, SN, NG, KE...) ou vide.
    categorie : paiement, donnees-publiques, administration, entreprises, telecoms,
    logistique, agriculture, sante, education, energie-mines, langues, autre.
    """
    s = session()
    try:
        req = select(Connecteur)
        if recherche.strip():
            m = f"%{recherche.strip()}%"
            req = req.where(or_(Connecteur.nom.ilike(m), Connecteur.resume.ilike(m),
                                Connecteur.service.ilike(m), Connecteur.description.ilike(m)))
        if pays:
            req = req.where(Connecteur.pays.like(f"%,{pays.strip().upper()},%"))
        if categorie:
            req = req.where(Connecteur.categorie == categorie.strip())
        cs = list(s.scalars(req.limit(25)))
        essais: dict[int, list[Essai]] = {c.id: [] for c in cs}
        if cs:
            for e in s.scalars(select(Essai).where(Essai.connecteur_id.in_(list(essais)))):
                essais[e.connecteur_id].append(e)
        return [_fiche(c, essais[c.id]) for c in cs]
    finally:
        s.close()


@serveur_mcp.tool()
def demandes_ouvertes(pays: str = "") -> list[dict]:
    """Connecteurs que des devs africains réclament et que personne n'a encore livrés.
    Utile pour savoir si un besoin est déjà exprimé avant d'en construire un."""
    s = session()
    try:
        req = select(Demande).where(Demande.statut != "resolue")
        if pays:
            req = req.where(Demande.pays.like(f"%,{pays.strip().upper()},%"))
        return [{"id": d.id, "titre": d.titre, "statut": d.statut,
                 "categorie": ref.CATEGORIES.get(d.categorie, d.categorie),
                 "pays": [ref.nom_pays(p) for p in d.codes_pays]}
                for d in s.scalars(req.order_by(Demande.cree_le.desc()).limit(25))]
    finally:
        s.close()


def routes_mcp():
    """Routes Starlette du serveur MCP, à greffer sur l'application FastAPI."""
    return serveur_mcp.streamable_http_app().routes
