"""Relevé GitHub et calcul de l'état « vivant » d'un connecteur.

Un connecteur vers un service africain casse souvent sans prévenir : l'opérateur
change son API, le ministère déplace son PDF. L'état affiché combine donc deux
sources indépendantes, et dit toujours pourquoi :
  - le dépôt : tests (GitHub Actions), dernier commit, archivage ;
  - la communauté : les derniers essais « ça marche / ça ne marche pas ».
"""
import os
import re
from datetime import datetime, timedelta

import httpx

from .db import Connecteur, Essai, maintenant
from .referentiel import LICENCES_COPYLEFT

_RE_GITHUB = re.compile(r"^https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")
FRAICHEUR = timedelta(hours=6)
FENETRE_ESSAIS = timedelta(days=60)
FENETRE_COMMIT = timedelta(days=180)


def depot_github(url: str) -> tuple[str, str] | None:
    m = _RE_GITHUB.match((url or "").strip())
    return (m.group(1), m.group(2)) if m else None


def _date_iso(texte: str | None) -> datetime | None:
    if not texte:
        return None
    return datetime.fromisoformat(texte.replace("Z", "+00:00")).replace(tzinfo=None)


def releve_a_faire(c: Connecteur) -> bool:
    return bool(depot_github(c.depot_url)) and (
        c.gh_verifie_le is None or maintenant() - c.gh_verifie_le > FRAICHEUR)


def relever_github(c: Connecteur, client: httpx.Client | None = None) -> None:
    """Met à jour les champs gh_* du connecteur. Ne lève jamais : l'erreur est stockée."""
    depot = depot_github(c.depot_url)
    c.gh_verifie_le = maintenant()
    if not depot:
        c.gh_erreur = "Dépôt hors GitHub : relevé automatique indisponible."
        return
    entetes = {"Accept": "application/vnd.github+json", "User-Agent": "relais-connecteurs"}
    if os.environ.get("GITHUB_TOKEN"):
        entetes["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    proprio = client is None
    client = client or httpx.Client(timeout=8, headers=entetes)
    try:
        r = client.get(f"https://api.github.com/repos/{depot[0]}/{depot[1]}", headers=entetes)
        if r.status_code == 404:
            c.gh_erreur = "Dépôt introuvable ou privé."
            return
        if r.status_code != 200:
            c.gh_erreur = f"GitHub a répondu {r.status_code}, nouvel essai plus tard."
            return
        d = r.json()
        c.gh_licence = ((d.get("license") or {}).get("spdx_id") or "").replace("NOASSERTION", "")
        c.gh_etoiles = int(d.get("stargazers_count") or 0)
        c.gh_dernier_push = _date_iso(d.get("pushed_at"))
        c.gh_archive = bool(d.get("archived"))
        c.gh_ci = ""
        branche = d.get("default_branch") or "main"
        r2 = client.get(f"https://api.github.com/repos/{depot[0]}/{depot[1]}/actions/runs",
                        params={"branch": branche, "per_page": 5, "status": "completed"},
                        headers=entetes)
        if r2.status_code == 200:
            for run in r2.json().get("workflow_runs", []):
                if run.get("conclusion") in ("success", "failure"):
                    c.gh_ci = run["conclusion"]
                    break
        c.gh_erreur = ""
    except httpx.HTTPError:
        c.gh_erreur = "GitHub injoignable, nouvel essai plus tard."
    finally:
        if proprio:
            client.close()


def etat(c: Connecteur, essais: list[Essai]) -> dict:
    """Renvoie {niveau: vivant|a-verifier|casse, libelle, raisons: [..]}."""
    raisons: list[str] = []
    t = maintenant()
    recents = [e for e in essais if t - e.le <= FENETRE_ESSAIS]
    dernier_ok = max((e.le for e in recents if e.marche), default=None)
    dernier_ko = max((e.le for e in recents if not e.marche), default=None)
    n_ok = sum(1 for e in recents if e.marche)
    n_ko = sum(1 for e in recents if not e.marche)

    casse = False
    if c.gh_archive:
        casse = True
        raisons.append("Le dépôt est archivé : il n'est plus maintenu.")
    if c.gh_ci == "failure":
        casse = True
        raisons.append("Les derniers tests automatiques du dépôt échouent.")
    if dernier_ko and (not dernier_ok or dernier_ko > dernier_ok):
        casse = True
        raisons.append("Le dernier essai signalé par un dev a échoué.")
    if casse:
        return {"niveau": "casse", "libelle": "Signalé cassé", "raisons": raisons}

    vivant = False
    if dernier_ok:
        vivant = True
        raisons.append(f"{n_ok} essai(s) réussi(s) ces 60 derniers jours"
                       + (f", {n_ko} échec(s) plus ancien(s)." if n_ko else "."))
    if c.gh_ci == "success":
        recent = c.gh_dernier_push and t - c.gh_dernier_push <= FENETRE_COMMIT
        if recent:
            vivant = True
        raisons.append("Les tests automatiques du dépôt passent"
                       + (" et le code a bougé ces 6 derniers mois." if recent else
                          ", mais aucun commit depuis plus de 6 mois."))
    if vivant:
        return {"niveau": "vivant", "libelle": "Vivant", "raisons": raisons}

    if not essais:
        raisons.append("Personne ne l'a encore essayé : soyez le premier.")
    elif not recents:
        raisons.append("Aucun essai depuis plus de 60 jours.")
    if not c.gh_ci and depot_github(c.depot_url):
        raisons.append("Le dépôt n'a pas de tests automatiques visibles.")
    return {"niveau": "a-verifier", "libelle": "À vérifier", "raisons": raisons}


def licence_copyleft(c: Connecteur) -> bool:
    return c.gh_licence in LICENCES_COPYLEFT
