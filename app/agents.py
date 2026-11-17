"""Serveur MCP de MCP for Africa : un agent IA peut chercher un connecteur africain
et savoir s'il marche encore, sans quitter la conversation.

Point d'entrée : POST /mcp, transport « streamable HTTP » sans état, réponses JSON.
Le protocole (JSON-RPC 2.0) est implémenté ici directement, sans SDK : trois
méthodes suffisent à un serveur d'outils en lecture seule, et cela évite une
vingtaine de dépendances dont une sous licence à réciprocité (MPL).
Spécification : https://modelcontextprotocol.io/specification/2025-06-18
"""
import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import or_, select

from . import referentiel as ref
from .db import Connecteur, Demande, Essai, session
from .etat import etat

VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]
INSTRUCTIONS = ("Catalogue communautaire de connecteurs vers les services africains "
                "(mobile money, données publiques, administrations). Chaque connecteur a un "
                "état « Vivant / À vérifier / Signalé cassé » tenu par la communauté, avec sa raison.")


def _fiche(c: Connecteur, essais: list[Essai]) -> dict:
    e = etat(c, essais)
    return {
        "slug": c.slug, "nom": c.nom, "resume": c.resume, "service": c.service,
        "categorie": ref.CATEGORIES.get(c.categorie, c.categorie),
        "type": ref.TYPES.get(c.type, c.type), "langage": c.langage,
        "pays": [ref.nom_pays(p) for p in c.codes_pays],
        "depot": c.depot_url, "licence": c.licence or "inconnue",
        "etat": e["libelle"], "pourquoi": e["raisons"],
        "installation": c.installation,
    }


def chercher_connecteurs(recherche: str = "", pays: str = "", categorie: str = "") -> list[dict]:
    s = session()
    try:
        req = select(Connecteur)
        if recherche.strip():
            m = f"%{recherche.strip()}%"
            req = req.where(or_(Connecteur.nom.ilike(m), Connecteur.resume.ilike(m),
                                Connecteur.service.ilike(m), Connecteur.description.ilike(m)))
        if pays.strip():
            req = req.where(Connecteur.pays.like(f"%,{pays.strip().upper()},%"))
        if categorie.strip():
            req = req.where(Connecteur.categorie == categorie.strip())
        cs = list(s.scalars(req.limit(25)))
        essais: dict[int, list[Essai]] = {c.id: [] for c in cs}
        if cs:
            for e in s.scalars(select(Essai).where(Essai.connecteur_id.in_(list(essais)))):
                essais[e.connecteur_id].append(e)
        return [_fiche(c, essais[c.id]) for c in cs]
    finally:
        s.close()


def demandes_ouvertes(pays: str = "") -> list[dict]:
    s = session()
    try:
        req = select(Demande).where(Demande.statut != "resolue")
        if pays.strip():
            req = req.where(Demande.pays.like(f"%,{pays.strip().upper()},%"))
        return [{"id": d.id, "titre": d.titre, "statut": d.statut,
                 "categorie": ref.CATEGORIES.get(d.categorie, d.categorie),
                 "pays": [ref.nom_pays(p) for p in d.codes_pays]}
                for d in s.scalars(req.order_by(Demande.cree_le.desc()).limit(25))]
    finally:
        s.close()


def _texte(description: str) -> dict:
    return {"type": "string", "description": description}


OUTILS = {
    "chercher_connecteurs": {
        "fonction": chercher_connecteurs,
        "description": ("Cherche des connecteurs vers des services africains et dit pour chacun "
                        "s'il marche encore, et pourquoi."),
        "proprietes": {
            "recherche": _texte("Mots-clés, ex. « orange money », « cadastre », « wave »."),
            "pays": _texte("Code ISO à deux lettres (BF, CI, SN, NG, KE…), ou vide."),
            "categorie": {"type": "string", "enum": [""] + list(ref.CATEGORIES),
                          "description": "Catégorie, ou vide."},
        },
    },
    "demandes_ouvertes": {
        "fonction": demandes_ouvertes,
        "description": ("Connecteurs que des devs africains réclament et que personne n'a encore "
                        "livrés : à consulter avant d'en construire un."),
        "proprietes": {"pays": _texte("Code ISO à deux lettres, ou vide.")},
    },
}


def _liste_outils() -> list[dict]:
    return [{"name": nom, "description": o["description"],
             "inputSchema": {"type": "object", "properties": o["proprietes"], "additionalProperties": False},
             "annotations": {"readOnlyHint": True, "openWorldHint": False}}
            for nom, o in OUTILS.items()]


def _erreur(ident, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": ident, "error": {"code": code, "message": message}}


def traiter(msg) -> dict | None:
    """Traite un message JSON-RPC ; None pour une notification (pas de réponse)."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return _erreur(msg.get("id") if isinstance(msg, dict) else None, -32600, "Requête invalide")
    ident, methode, params = msg.get("id"), msg["method"], msg.get("params") or {}
    if "id" not in msg:
        return None  # notifications/initialized, notifications/cancelled…
    if methode == "initialize":
        demandee = params.get("protocolVersion")
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "protocolVersion": demandee if demandee in VERSIONS else VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "mcp-for-africa", "version": "1.0.0"},
            "instructions": INSTRUCTIONS}}
    if methode == "ping":
        return {"jsonrpc": "2.0", "id": ident, "result": {}}
    if methode == "tools/list":
        return {"jsonrpc": "2.0", "id": ident, "result": {"tools": _liste_outils()}}
    if methode == "tools/call":
        outil = OUTILS.get(params.get("name"))
        if not outil:
            return _erreur(ident, -32602, f"Outil inconnu : {params.get('name')}")
        args = params.get("arguments") or {}
        if not isinstance(args, dict) or set(args) - set(outil["proprietes"]) \
                or not all(isinstance(v, str) for v in args.values()):
            return _erreur(ident, -32602, "Arguments invalides : chaînes attendues, voir inputSchema.")
        try:
            resultat = outil["fonction"](**args)
        except Exception:  # l'erreur d'un outil se signale dans le résultat, pas en JSON-RPC
            return {"jsonrpc": "2.0", "id": ident, "result": {
                "isError": True, "content": [{"type": "text", "text": "Erreur interne, réessayez."}]}}
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "isError": False,
            "content": [{"type": "text", "text": json.dumps(resultat, ensure_ascii=False, default=str)}]}}
    return _erreur(ident, -32601, f"Méthode inconnue : {methode}")


routeur = APIRouter()


@routeur.post("/mcp", include_in_schema=False)
async def point_mcp(request: Request):
    try:
        corps = json.loads(await request.body())
    except (ValueError, UnicodeDecodeError):
        return JSONResponse(_erreur(None, -32700, "JSON invalide"), status_code=400)
    if isinstance(corps, list):  # lot (batch)
        reponses = [r for r in (traiter(m) for m in corps[:20]) if r is not None]
        return JSONResponse(reponses) if reponses else Response(status_code=202)
    reponse = traiter(corps)
    return JSONResponse(reponse) if reponse is not None else Response(status_code=202)


@routeur.get("/mcp", include_in_schema=False)
@routeur.delete("/mcp", include_in_schema=False)
async def mcp_sans_flux():
    # Serveur sans état : pas de flux SSE ni de session à fermer.
    return Response(status_code=405, headers={"Allow": "POST"})
