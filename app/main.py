"""Relais — les connecteurs africains, construits ensemble."""
import contextlib
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from markupsafe import Markup
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from . import referentiel as ref
from .db import (Connecteur, Contributeur, Demande, Dev, Essai, Message,
                 Soutien, creer_tables, maintenant, session as nouvelle_session)
from .etat import depot_github, etat, licence_copyleft, relever_github, releve_a_faire
from .securite import Limiteur, csrf_valide, hacher, jeton_csrf, verifier

ICI = Path(__file__).parent
SECRET = os.environ.get("SECRET_KEY") or "dev-local-seulement-changer-en-production"
EN_PROD = os.environ.get("RELAIS_ENV") == "production"
if EN_PROD and SECRET.startswith("dev-local"):
    raise RuntimeError("SECRET_KEY doit être défini en production.")

limite_connexion = Limiteur(8, 600)
limite_ecriture = Limiteur(40, 600)


@contextlib.asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    creer_tables()
    if os.environ.get("RELAIS_AMORCE", "1") == "1":
        from .amorce import amorcer
        amorcer()
    from .agents import serveur_mcp
    async with serveur_mcp.session_manager.run():
        yield


app = FastAPI(title="Relais", lifespan=cycle_de_vie, docs_url="/api/docs", redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=SECRET, max_age=30 * 24 * 3600,
                   same_site="lax", https_only=EN_PROD, session_cookie="relais")
app.mount("/static", StaticFiles(directory=ICI / "static"), name="static")

# Le serveur MCP de la plateforme elle-même, sur /mcp (voir agents.py).
from .agents import routes_mcp  # noqa: E402
app.router.routes.extend(routes_mcp())

gabarits = Jinja2Templates(directory=ICI / "templates")
_md = MarkdownIt("commonmark", {"html": False, "linkify": False, "breaks": True}).enable("table")


def _markdown(texte: str) -> Markup:
    return Markup(_md.render(texte or ""))


def _il_y_a(d) -> str:
    if not d:
        return "jamais"
    s = int((maintenant() - d).total_seconds())
    if s < 60:
        return "à l'instant"
    for unite, taille in (("an", 31536000), ("mois", 2592000), ("j", 86400), ("h", 3600), ("min", 60)):
        if s >= taille:
            n = s // taille
            if unite == "an" and n > 1:
                unite = "ans"
            return f"il y a {n} {unite}"
    return ""


gabarits.env.filters.update(md=_markdown, il_y_a=_il_y_a, drapeau=ref.drapeau, nom_pays=ref.nom_pays)
gabarits.env.globals.update(ref=ref)


# ------------------------------------------------------------------ outils

def bd():
    s = nouvelle_session()
    try:
        yield s
    finally:
        s.close()


def dev_courant(request: Request, s: Session) -> Dev | None:
    did = request.session.get("dev_id")
    return s.get(Dev, did) if did else None


def flash(request: Request, texte: str, genre: str = "ok") -> None:
    request.session.setdefault("flash", []).append([genre, texte])


def rendre(request: Request, s: Session, gabarit: str, statut: int = 200, **ctx) -> HTMLResponse:
    ctx.update(request=request, moi=dev_courant(request, s), csrf=jeton_csrf(request.session),
               messages_flash=request.session.pop("flash", []))
    return gabarits.TemplateResponse(request, gabarit, ctx, status_code=statut)


def vers(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


async def formulaire(request: Request):
    f = await request.form()
    if not csrf_valide(request.session, f.get("csrf")):
        raise HTTPException(400, "Formulaire expiré : rechargez la page et recommencez.")
    return f


def exiger(request: Request, s: Session) -> Dev:
    moi = dev_courant(request, s)
    if not moi:
        raise HTTPException(401)
    ip = request.client.host if request.client else "?"
    if request.method == "POST" and not limite_ecriture.autorise(f"{moi.id}:{ip}"):
        raise HTTPException(429, "Trop d'actions en peu de temps : patientez quelques minutes.")
    return moi


def slugifier(texte: str) -> str:
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:70] or "connecteur"


def slug_libre(s: Session, base: str) -> str:
    slug, n = base, 2
    while s.scalar(select(Connecteur.id).where(Connecteur.slug == slug)):
        slug, n = f"{base}-{n}", n + 1
    return slug


def pays_champ(codes: list[str]) -> str:
    return ("," + ",".join(codes) + ",") if codes else ""


def url_valide(u: str) -> str:
    u = (u or "").strip()
    return u if re.match(r"^https?://[^\s<>\"']+$", u) else ""


def essais_de(s: Session, cid: int) -> list[Essai]:
    return list(s.scalars(select(Essai).where(Essai.connecteur_id == cid).order_by(Essai.le.desc())))


def etats(s: Session, connecteurs: list[Connecteur]) -> dict[int, dict]:
    ids = [c.id for c in connecteurs]
    par_c: dict[int, list[Essai]] = defaultdict(list)
    if ids:
        for e in s.scalars(select(Essai).where(Essai.connecteur_id.in_(ids))):
            par_c[e.connecteur_id].append(e)
    return {c.id: etat(c, par_c[c.id]) for c in connecteurs}


def relever_en_arriere_plan(cid: int) -> None:
    s = nouvelle_session()
    try:
        c = s.get(Connecteur, cid)
        if c and releve_a_faire(c):
            relever_github(c)
            s.commit()
    finally:
        s.close()


@app.exception_handler(HTTPException)
async def erreur_http(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"erreur": exc.detail}, status_code=exc.status_code)
    if exc.status_code == 401:
        return vers(f"/connexion?suite={request.url.path}")
    s = nouvelle_session()
    try:
        textes = {404: "Cette page n'existe pas (ou plus).", 403: "Cette action ne vous est pas permise."}
        detail = exc.detail if isinstance(exc.detail, str) and exc.detail not in ("Not Found", "Forbidden") else ""
        return rendre(request, s, "erreur.html", statut=exc.status_code,
                      texte=detail or textes.get(exc.status_code, "Une erreur est survenue."))
    finally:
        s.close()


# ------------------------------------------------------------------ statistiques

def points_par_dev(s: Session) -> Counter:
    p: Counter = Counter()
    for did, n in s.execute(select(Connecteur.auteur_id, func.count()).group_by(Connecteur.auteur_id)):
        p[did] += 10 * n
    for did, n in s.execute(select(Demande.preneur_id, func.count()).where(Demande.statut == "resolue")
                            .group_by(Demande.preneur_id)):
        if did:
            p[did] += 15 * n
    for did, n in s.execute(select(Essai.dev_id, func.count()).group_by(Essai.dev_id)):
        p[did] += 2 * n
    for did, n in s.execute(select(Contributeur.dev_id, func.count()).group_by(Contributeur.dev_id)):
        p[did] += 3 * n
    for did, n in s.execute(select(Message.dev_id, func.count()).group_by(Message.dev_id)):
        p[did] += 1 * n
    for did, n in s.execute(select(Demande.auteur_id, func.count()).group_by(Demande.auteur_id)):
        p[did] += 1 * n
    return p


def couverture(s: Session) -> dict:
    """Par pays : connecteurs, demandes ouvertes, et matrice pays x catégorie."""
    par_pays: Counter = Counter()
    matrice: dict[str, Counter] = defaultdict(Counter)
    for c in s.scalars(select(Connecteur)):
        for code in c.codes_pays:
            par_pays[code] += 1
            matrice[code][c.categorie] += 1
    attente: Counter = Counter()
    for d in s.scalars(select(Demande).where(Demande.statut != "resolue")):
        for code in d.codes_pays:
            attente[code] += 1
    return {"par_pays": par_pays, "matrice": matrice, "attente": attente}


# ------------------------------------------------------------------ pages publiques

@app.get("/sante")
def sante():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def accueil(request: Request, s: Session = Depends(bd)):
    recents = list(s.scalars(select(Connecteur).order_by(Connecteur.cree_le.desc()).limit(6)))
    nb_soutiens = func.count(Soutien.id)
    demandes = list(s.execute(
        select(Demande, nb_soutiens).outerjoin(Soutien, Soutien.demande_id == Demande.id)
        .where(Demande.statut != "resolue").group_by(Demande.id)
        .order_by(nb_soutiens.desc(), Demande.cree_le.desc()).limit(5)))
    cov = couverture(s)
    chiffres = {
        "connecteurs": s.scalar(select(func.count(Connecteur.id))) or 0,
        "pays": len(cov["par_pays"]),
        "devs": s.scalar(select(func.count(Dev.id))) or 0,
        "essais": s.scalar(select(func.count(Essai.id))) or 0,
        "demandes": s.scalar(select(func.count(Demande.id)).where(Demande.statut != "resolue")) or 0,
    }
    return rendre(request, s, "accueil.html", recents=recents, etats=etats(s, recents),
                  demandes=demandes, chiffres=chiffres, cov=cov)


@app.get("/connecteurs", response_class=HTMLResponse)
def liste_connecteurs(request: Request, q: str = "", pays: str = "", categorie: str = "",
                      type: str = "", s: Session = Depends(bd)):
    req = select(Connecteur)
    if q.strip():
        motif = f"%{q.strip()}%"
        req = req.where(or_(Connecteur.nom.ilike(motif), Connecteur.resume.ilike(motif),
                            Connecteur.service.ilike(motif), Connecteur.description.ilike(motif)))
    if pays in ref.PAYS:
        req = req.where(Connecteur.pays.like(f"%,{pays},%"))
    if categorie in ref.CATEGORIES:
        req = req.where(Connecteur.categorie == categorie)
    if type in ref.TYPES:
        req = req.where(Connecteur.type == type)
    connecteurs = list(s.scalars(req.order_by(Connecteur.modifie_le.desc())))
    e = etats(s, connecteurs)
    etat_filtre = request.query_params.get("etat", "")
    if etat_filtre in ("vivant", "a-verifier", "casse"):
        connecteurs = [c for c in connecteurs if e[c.id]["niveau"] == etat_filtre]
    return rendre(request, s, "connecteurs.html", connecteurs=connecteurs, etats=e,
                  f={"q": q, "pays": pays, "categorie": categorie, "type": type, "etat": etat_filtre})


def charger_connecteur(s: Session, slug: str) -> Connecteur:
    c = s.scalar(select(Connecteur).where(Connecteur.slug == slug))
    if not c:
        raise HTTPException(404)
    return c


def peut_modifier(s: Session, c: Connecteur, moi: Dev | None) -> bool:
    if not moi:
        return False
    if c.auteur_id == moi.id:
        return True
    return bool(s.scalar(select(Contributeur.id).where(Contributeur.connecteur_id == c.id,
                                                       Contributeur.dev_id == moi.id)))


@app.get("/connecteurs/nouveau", response_class=HTMLResponse)
def nouveau_connecteur(request: Request, demande: int | None = None, s: Session = Depends(bd)):
    exiger(request, s)
    d = s.get(Demande, demande) if demande else None
    pre = Connecteur(nom="", resume="", categorie=d.categorie if d else "", type="mcp",
                     pays=d.pays if d else "", description="", installation="")
    return rendre(request, s, "connecteur_form.html", c=pre, nouveau=True, demande=d, erreurs=[])


def _lire_connecteur(f, c: Connecteur) -> list[str]:
    erreurs = []
    c.nom = (f.get("nom") or "").strip()[:80]
    c.resume = (f.get("resume") or "").strip()[:200]
    c.description = (f.get("description") or "").strip()[:20000]
    c.installation = (f.get("installation") or "").strip()[:4000]
    c.categorie = f.get("categorie") or ""
    c.type = f.get("type") or ""
    c.langage = (f.get("langage") or "")[:40]
    c.service = (f.get("service") or "").strip()[:120]
    c.pays = pays_champ(ref.pays_depuis_formulaire(f.getlist("pays")))
    c.depot_url = url_valide(f.get("depot_url"))
    c.doc_url = url_valide(f.get("doc_url"))
    if len(c.nom) < 3:
        erreurs.append("Le nom doit faire au moins 3 caractères.")
    if len(c.resume) < 10:
        erreurs.append("Le résumé doit faire au moins 10 caractères.")
    if c.categorie not in ref.CATEGORIES:
        erreurs.append("Choisissez une catégorie.")
    if c.type not in ref.TYPES:
        erreurs.append("Choisissez un type.")
    if not c.pays:
        erreurs.append("Indiquez au moins un pays couvert.")
    if (f.get("depot_url") or "").strip() and not c.depot_url:
        erreurs.append("L'adresse du dépôt doit commencer par https://.")
    if not c.depot_url:
        erreurs.append("Un connecteur se partage par son code : indiquez l'adresse du dépôt.")
    return erreurs


@app.post("/connecteurs/nouveau")
async def creer_connecteur(request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    f = await formulaire(request)
    c = Connecteur(auteur_id=moi.id)
    erreurs = _lire_connecteur(f, c)
    demande = s.get(Demande, int(f["demande"])) if (f.get("demande") or "").isdigit() else None
    if erreurs:
        return rendre(request, s, "connecteur_form.html", statut=422, c=c, nouveau=True,
                      demande=demande, erreurs=erreurs)
    c.slug = slug_libre(s, slugifier(c.nom))
    relever_github(c)
    s.add(c)
    s.flush()
    if demande and demande.statut != "resolue":
        demande.statut, demande.connecteur_id = "resolue", c.id
        demande.preneur_id = demande.preneur_id or moi.id
    s.commit()
    flash(request, "Connecteur publié. Merci pour la communauté !")
    return vers(f"/connecteurs/{c.slug}")


@app.get("/connecteurs/{slug}", response_class=HTMLResponse)
def fiche_connecteur(slug: str, request: Request, taches: BackgroundTasks, s: Session = Depends(bd)):
    c = charger_connecteur(s, slug)
    if releve_a_faire(c):
        taches.add_task(relever_en_arriere_plan, c.id)
    essais = essais_de(s, c.id)
    moi = dev_courant(request, s)
    contributeurs = list(s.scalars(select(Contributeur).where(Contributeur.connecteur_id == c.id)
                                   .order_by(Contributeur.le)))
    messages = list(s.scalars(select(Message).where(Message.cible == "connecteur", Message.cible_id == c.id)
                              .order_by(Message.le)))
    demandes = list(s.scalars(select(Demande).where(Demande.connecteur_id == c.id)))
    mon_essai = next((e for e in essais if moi and e.dev_id == moi.id), None)
    return rendre(request, s, "connecteur.html", c=c, e=etat(c, essais), essais=essais,
                  contributeurs=contributeurs, messages=messages, demandes=demandes,
                  mon_essai=mon_essai, modifiable=peut_modifier(s, c, moi),
                  deja_contributeur=any(x.dev_id == (moi.id if moi else 0) for x in contributeurs),
                  copyleft=licence_copyleft(c), sur_github=bool(depot_github(c.depot_url)))


@app.get("/connecteurs/{slug}/modifier", response_class=HTMLResponse)
def modifier_connecteur(slug: str, request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    c = charger_connecteur(s, slug)
    if not peut_modifier(s, c, moi):
        raise HTTPException(403)
    return rendre(request, s, "connecteur_form.html", c=c, nouveau=False, demande=None, erreurs=[])


@app.post("/connecteurs/{slug}/modifier")
async def enregistrer_connecteur(slug: str, request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    c = charger_connecteur(s, slug)
    if not peut_modifier(s, c, moi):
        raise HTTPException(403)
    f = await formulaire(request)
    ancien_depot = c.depot_url
    erreurs = _lire_connecteur(f, c)
    if erreurs:
        s.rollback()
        return rendre(request, s, "connecteur_form.html", statut=422, c=c, nouveau=False,
                      demande=None, erreurs=erreurs)
    c.modifie_le = maintenant()
    if c.depot_url != ancien_depot:
        relever_github(c)
    s.commit()
    flash(request, "Fiche mise à jour.")
    return vers(f"/connecteurs/{c.slug}")


@app.post("/connecteurs/{slug}/essai")
async def noter_essai(slug: str, request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    c = charger_connecteur(s, slug)
    f = await formulaire(request)
    marche = f.get("marche") == "oui"
    pays = f.get("pays") if f.get("pays") in ref.PAYS else moi.pays
    note = (f.get("note") or "").strip()[:500]
    if not marche and len(note) < 5:
        flash(request, "Dites en une phrase ce qui ne marche pas : c'est ce qui aide à réparer.", "erreur")
        return vers(f"/connecteurs/{slug}#essayer")
    e = s.scalar(select(Essai).where(Essai.connecteur_id == c.id, Essai.dev_id == moi.id))
    if not e:
        e = Essai(connecteur_id=c.id, dev_id=moi.id)
        s.add(e)
    e.marche, e.pays, e.note, e.le = marche, pays or "", note, maintenant()
    s.commit()
    flash(request, "Merci : votre essai met à jour l'état du connecteur pour tout le monde.")
    return vers(f"/connecteurs/{slug}#essais")


@app.post("/connecteurs/{slug}/rejoindre")
async def rejoindre(slug: str, request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    c = charger_connecteur(s, slug)
    f = await formulaire(request)
    if c.auteur_id == moi.id:
        return vers(f"/connecteurs/{slug}")
    role = (f.get("role") or "").strip()[:200] or "Contributeur"
    s.add(Contributeur(connecteur_id=c.id, dev_id=moi.id, role=role))
    try:
        s.commit()
        flash(request, "Vous faites maintenant partie de l'équipe de ce connecteur.")
    except IntegrityError:
        s.rollback()
    return vers(f"/connecteurs/{slug}#equipe")


@app.post("/connecteurs/{slug}/relever")
async def relever(slug: str, request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    c = charger_connecteur(s, slug)
    await formulaire(request)
    if not peut_modifier(s, c, moi):
        raise HTTPException(403)
    relever_github(c)
    s.commit()
    flash(request, c.gh_erreur or "Dépôt relu à l'instant.", "erreur" if c.gh_erreur else "ok")
    return vers(f"/connecteurs/{slug}")


def _poster_message(s: Session, moi: Dev, cible: str, cible_id: int, texte: str) -> bool:
    texte = (texte or "").strip()[:5000]
    if len(texte) < 2:
        return False
    s.add(Message(cible=cible, cible_id=cible_id, dev_id=moi.id, texte=texte))
    s.commit()
    return True


@app.post("/connecteurs/{slug}/message")
async def message_connecteur(slug: str, request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    c = charger_connecteur(s, slug)
    f = await formulaire(request)
    _poster_message(s, moi, "connecteur", c.id, f.get("texte"))
    return vers(f"/connecteurs/{slug}#discussion")


# ------------------------------------------------------------------ demandes

@app.get("/demandes", response_class=HTMLResponse)
def liste_demandes(request: Request, statut: str = "ouvertes", pays: str = "", categorie: str = "",
                   s: Session = Depends(bd)):
    nb = func.count(Soutien.id)
    req = select(Demande, nb).outerjoin(Soutien, Soutien.demande_id == Demande.id).group_by(Demande.id)
    if statut == "ouvertes":
        req = req.where(Demande.statut != "resolue")
    elif statut == "resolues":
        req = req.where(Demande.statut == "resolue")
    if pays in ref.PAYS:
        req = req.where(Demande.pays.like(f"%,{pays},%"))
    if categorie in ref.CATEGORIES:
        req = req.where(Demande.categorie == categorie)
    lignes = list(s.execute(req.order_by(nb.desc(), Demande.cree_le.desc())))
    moi = dev_courant(request, s)
    soutenues = set()
    if moi:
        soutenues = set(s.scalars(select(Soutien.demande_id).where(Soutien.dev_id == moi.id)))
    return rendre(request, s, "demandes.html", lignes=lignes, soutenues=soutenues,
                  f={"statut": statut, "pays": pays, "categorie": categorie})


@app.get("/demandes/nouvelle", response_class=HTMLResponse)
def nouvelle_demande(request: Request, s: Session = Depends(bd)):
    exiger(request, s)
    return rendre(request, s, "demande_form.html", d=Demande(titre="", description="", categorie="", pays=""),
                  erreurs=[])


@app.post("/demandes/nouvelle")
async def creer_demande(request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    f = await formulaire(request)
    d = Demande(auteur_id=moi.id, titre=(f.get("titre") or "").strip()[:140],
                description=(f.get("description") or "").strip()[:10000],
                categorie=f.get("categorie") or "",
                pays=pays_champ(ref.pays_depuis_formulaire(f.getlist("pays"))))
    erreurs = []
    if len(d.titre) < 8:
        erreurs.append("Le titre doit dire en quelques mots ce qu'il vous faut (8 caractères minimum).")
    if d.categorie not in ref.CATEGORIES:
        erreurs.append("Choisissez une catégorie.")
    if not d.pays:
        erreurs.append("Indiquez au moins un pays.")
    if erreurs:
        return rendre(request, s, "demande_form.html", statut=422, d=d, erreurs=erreurs)
    s.add(d)
    s.flush()
    s.add(Soutien(demande_id=d.id, dev_id=moi.id))
    s.commit()
    flash(request, "Demande publiée. Les devs qui ont le même besoin peuvent la soutenir.")
    return vers(f"/demandes/{d.id}")


def charger_demande(s: Session, did: int) -> Demande:
    d = s.get(Demande, did)
    if not d:
        raise HTTPException(404)
    return d


@app.get("/demandes/{did}", response_class=HTMLResponse)
def fiche_demande(did: int, request: Request, s: Session = Depends(bd)):
    d = charger_demande(s, did)
    moi = dev_courant(request, s)
    soutiens = list(s.execute(select(Dev).join(Soutien, Soutien.dev_id == Dev.id)
                              .where(Soutien.demande_id == d.id).order_by(Soutien.le)).scalars())
    messages = list(s.scalars(select(Message).where(Message.cible == "demande", Message.cible_id == d.id)
                              .order_by(Message.le)))
    mes_connecteurs = []
    if moi:
        mes_connecteurs = list(s.scalars(select(Connecteur).where(Connecteur.auteur_id == moi.id)
                                         .order_by(Connecteur.nom)))
    return rendre(request, s, "demande.html", d=d, soutiens=soutiens, messages=messages,
                  je_soutiens=any(x.id == (moi.id if moi else 0) for x in soutiens),
                  mes_connecteurs=mes_connecteurs)


@app.post("/demandes/{did}/soutenir")
async def soutenir(did: int, request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    d = charger_demande(s, did)
    f = await formulaire(request)
    existant = s.scalar(select(Soutien).where(Soutien.demande_id == d.id, Soutien.dev_id == moi.id))
    if existant:
        s.delete(existant)
    else:
        s.add(Soutien(demande_id=d.id, dev_id=moi.id))
    s.commit()
    retour = f.get("retour") or f"/demandes/{did}"
    return vers(retour if retour.startswith("/") and not retour.startswith("//") else f"/demandes/{did}")


@app.post("/demandes/{did}/prendre")
async def prendre(did: int, request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    d = charger_demande(s, did)
    await formulaire(request)
    if d.statut == "ouverte":
        d.statut, d.preneur_id = "en-cours", moi.id
        s.add(Message(cible="demande", cible_id=d.id, dev_id=moi.id,
                      texte="Je m'en occupe. Je publierai le connecteur ici dès qu'il marche."))
        s.commit()
        flash(request, "C'est noté : la demande est à vous. Publiez le connecteur quand il est prêt.")
    elif d.statut == "en-cours" and d.preneur_id == moi.id:
        d.statut, d.preneur_id = "ouverte", None
        s.commit()
        flash(request, "Demande rendue à la communauté.")
    return vers(f"/demandes/{did}")


@app.post("/demandes/{did}/resoudre")
async def resoudre(did: int, request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    d = charger_demande(s, did)
    f = await formulaire(request)
    c = s.scalar(select(Connecteur).where(Connecteur.slug == (f.get("connecteur") or "")))
    if not c or c.auteur_id != moi.id or d.statut == "resolue":
        flash(request, "Choisissez un de vos connecteurs publiés.", "erreur")
        return vers(f"/demandes/{did}")
    d.statut, d.connecteur_id, d.preneur_id = "resolue", c.id, moi.id
    s.add(Message(cible="demande", cible_id=d.id, dev_id=moi.id,
                  texte=f"Résolu avec le connecteur **{c.nom}**."))
    s.commit()
    flash(request, "Demande résolue : tous ceux qui la soutenaient trouveront votre connecteur ici.")
    return vers(f"/demandes/{did}")


@app.post("/demandes/{did}/message")
async def message_demande(did: int, request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    d = charger_demande(s, did)
    f = await formulaire(request)
    _poster_message(s, moi, "demande", d.id, f.get("texte"))
    return vers(f"/demandes/{did}#discussion")


# ------------------------------------------------------------------ carte, devs, classement

@app.get("/carte", response_class=HTMLResponse)
def carte(request: Request, s: Session = Depends(bd)):
    return rendre(request, s, "carte.html", cov=couverture(s))


@app.get("/devs/{pseudo}", response_class=HTMLResponse)
def profil_public(pseudo: str, request: Request, s: Session = Depends(bd)):
    d = s.scalar(select(Dev).where(Dev.pseudo == pseudo))
    if not d:
        raise HTTPException(404)
    publies = list(s.scalars(select(Connecteur).where(Connecteur.auteur_id == d.id)
                             .order_by(Connecteur.cree_le.desc())))
    contribue = list(s.scalars(select(Connecteur).join(Contributeur, Contributeur.connecteur_id == Connecteur.id)
                               .where(Contributeur.dev_id == d.id)))
    essais = list(s.scalars(select(Essai).where(Essai.dev_id == d.id).order_by(Essai.le.desc()).limit(20)))
    resolues = list(s.scalars(select(Demande).where(Demande.preneur_id == d.id, Demande.statut == "resolue")))
    tous = publies + contribue
    return rendre(request, s, "dev.html", d=d, publies=publies, contribue=contribue, essais=essais,
                  resolues=resolues, points=points_par_dev(s)[d.id], etats=etats(s, tous))


@app.get("/classement", response_class=HTMLResponse)
def classement(request: Request, s: Session = Depends(bd)):
    p = points_par_dev(s)
    devs = {d.id: d for d in s.scalars(select(Dev))}
    top = [(devs[i], n) for i, n in p.most_common() if i in devs and n > 0][:50]
    par_pays: Counter = Counter()
    for i, n in p.items():
        if i in devs and devs[i].pays:
            par_pays[devs[i].pays] += n
    return rendre(request, s, "classement.html", top=top, pays=par_pays.most_common())


@app.get("/a-propos", response_class=HTMLResponse)
def a_propos(request: Request, s: Session = Depends(bd)):
    return rendre(request, s, "a_propos.html", url_mcp=str(request.base_url).rstrip("/") + "/mcp")


# ------------------------------------------------------------------ comptes

_RE_PSEUDO = re.compile(r"^[A-Za-z0-9_-]{3,30}$")


@app.get("/inscription", response_class=HTMLResponse)
def inscription(request: Request, s: Session = Depends(bd)):
    return rendre(request, s, "inscription.html", v={}, erreurs=[])


@app.post("/inscription")
async def inscrire(request: Request, s: Session = Depends(bd)):
    f = await formulaire(request)
    ip = request.client.host if request.client else "?"
    v = {k: (f.get(k) or "").strip() for k in ("pseudo", "email", "pays", "github")}
    erreurs = []
    if not _RE_PSEUDO.match(v["pseudo"]):
        erreurs.append("Pseudo : 3 à 30 caractères, lettres, chiffres, - ou _.")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v["email"]):
        erreurs.append("Adresse e-mail invalide.")
    if len(f.get("mdp") or "") < 8:
        erreurs.append("Mot de passe : 8 caractères minimum.")
    if v["pays"] not in ref.PAYS:
        erreurs.append("Choisissez votre pays.")
    if not erreurs and not limite_connexion.autorise("inscription:" + ip):
        erreurs.append("Trop de tentatives : réessayez dans quelques minutes.")
    if not erreurs:
        if s.scalar(select(Dev.id).where(func.lower(Dev.pseudo) == v["pseudo"].lower())):
            erreurs.append("Ce pseudo est déjà pris.")
        if s.scalar(select(Dev.id).where(func.lower(Dev.email) == v["email"].lower())):
            erreurs.append("Un compte existe déjà avec cette adresse.")
    if erreurs:
        return rendre(request, s, "inscription.html", statut=422, v=v, erreurs=erreurs)
    d = Dev(pseudo=v["pseudo"], email=v["email"].lower(), mdp=hacher(f["mdp"]), pays=v["pays"],
            github=re.sub(r"[^A-Za-z0-9-]", "", v["github"])[:39])
    s.add(d)
    s.commit()
    request.session.clear()
    request.session["dev_id"] = d.id
    flash(request, f"Bienvenue {d.pseudo} ! Essayez un connecteur ou publiez le vôtre.")
    return vers("/connecteurs")


@app.get("/connexion", response_class=HTMLResponse)
def connexion(request: Request, suite: str = "/", s: Session = Depends(bd)):
    return rendre(request, s, "connexion.html", suite=suite, erreur="")


@app.post("/connexion")
async def connecter(request: Request, s: Session = Depends(bd)):
    f = await formulaire(request)
    ident = (f.get("identifiant") or "").strip().lower()
    suite = f.get("suite") or "/"
    if not suite.startswith("/") or suite.startswith("//"):
        suite = "/"
    ip = request.client.host if request.client else "?"
    if not limite_connexion.autorise(f"{ip}:{ident}"):
        return rendre(request, s, "connexion.html", statut=429, suite=suite,
                      erreur="Trop de tentatives : réessayez dans 10 minutes.")
    d = s.scalar(select(Dev).where(or_(func.lower(Dev.email) == ident, func.lower(Dev.pseudo) == ident)))
    if not d or not verifier(f.get("mdp") or "", d.mdp):
        return rendre(request, s, "connexion.html", statut=401, suite=suite,
                      erreur="Identifiant ou mot de passe incorrect.")
    request.session.clear()
    request.session["dev_id"] = d.id
    return vers(suite)


@app.post("/deconnexion")
async def deconnecter(request: Request):
    await formulaire(request)
    request.session.clear()
    return vers("/")


@app.get("/profil", response_class=HTMLResponse)
def mon_profil(request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    return rendre(request, s, "profil.html", d=moi)


@app.post("/profil")
async def enregistrer_profil(request: Request, s: Session = Depends(bd)):
    moi = exiger(request, s)
    f = await formulaire(request)
    if f.get("pays") in ref.PAYS:
        moi.pays = f["pays"]
    moi.bio = (f.get("bio") or "").strip()[:1000]
    moi.github = re.sub(r"[^A-Za-z0-9-]", "", f.get("github") or "")[:39]
    s.commit()
    flash(request, "Profil enregistré.")
    return vers(f"/devs/{moi.pseudo}")


# ------------------------------------------------------------------ API JSON publique

def connecteur_json(c: Connecteur, e: dict, base: str) -> dict:
    return {
        "slug": c.slug, "nom": c.nom, "resume": c.resume, "service": c.service,
        "categorie": c.categorie, "type": c.type, "langage": c.langage,
        "pays": c.codes_pays, "depot": c.depot_url, "documentation": c.doc_url,
        "licence": c.gh_licence, "etat": e["niveau"], "raisons_etat": e["raisons"],
        "installation": c.installation, "fiche": f"{base}/connecteurs/{c.slug}",
        "auteur": c.auteur.pseudo,
    }


@app.get("/api/connecteurs")
def api_connecteurs(request: Request, pays: str = "", categorie: str = "", s: Session = Depends(bd)):
    req = select(Connecteur)
    if pays:
        req = req.where(Connecteur.pays.like(f"%,{pays.upper()},%"))
    if categorie:
        req = req.where(Connecteur.categorie == categorie)
    cs = list(s.scalars(req.order_by(Connecteur.nom)))
    e = etats(s, cs)
    base = str(request.base_url).rstrip("/")
    return [connecteur_json(c, e[c.id], base) for c in cs]


@app.get("/api/connecteurs/{slug}")
def api_connecteur(slug: str, request: Request, s: Session = Depends(bd)):
    c = charger_connecteur(s, slug)
    return connecteur_json(c, etat(c, essais_de(s, c.id)), str(request.base_url).rstrip("/"))


@app.get("/api/demandes")
def api_demandes(request: Request, s: Session = Depends(bd)):
    nb = func.count(Soutien.id)
    lignes = s.execute(select(Demande, nb).outerjoin(Soutien, Soutien.demande_id == Demande.id)
                       .where(Demande.statut != "resolue").group_by(Demande.id).order_by(nb.desc()))
    base = str(request.base_url).rstrip("/")
    return [{"id": d.id, "titre": d.titre, "categorie": d.categorie, "pays": d.codes_pays,
             "statut": d.statut, "soutiens": n, "fiche": f"{base}/demandes/{d.id}"} for d, n in lignes]


@app.get("/robots.txt", response_class=HTMLResponse)
def robots():
    return HTMLResponse("User-agent: *\nAllow: /\n", media_type="text/plain")

