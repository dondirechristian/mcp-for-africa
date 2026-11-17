"""Parcours complets sur une base SQLite temporaire, sans réseau."""
import json
import os
import re
import tempfile
from datetime import timedelta

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["MFA_AMORCE_RELEVE"] = "0"  # pas d'appel à GitHub pendant les tests

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import etat as module_etat  # noqa: E402
from app.db import Connecteur, Essai, maintenant  # noqa: E402
from app.main import app  # noqa: E402
from app.securite import hacher, verifier  # noqa: E402


@pytest.fixture(autouse=True)
def sans_github(monkeypatch):
    def faux_releve(c):
        c.gh_verifie_le = maintenant()
        c.gh_licence, c.gh_ci = "MIT", ""
    monkeypatch.setattr("app.main.relever_github", faux_releve)
    monkeypatch.setattr("app.main.releve_a_faire", lambda c: False)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def csrf(client, url):
    r = client.get(url)
    assert r.status_code == 200, (url, r.status_code)
    return re.search(r'name="csrf" value="([^"]+)"', r.text).group(1)


def inscrire(client, pseudo, pays="BF"):
    client.cookies.clear()
    jeton = csrf(client, "/inscription")
    r = client.post("/inscription", data={"csrf": jeton, "pseudo": pseudo, "email": f"{pseudo}@exemple.org",
                                          "mdp": "motdepasse-solide", "pays": pays}, follow_redirects=False)
    assert r.status_code == 303, r.text
    return client


def test_mot_de_passe():
    h = hacher("secret123")
    assert verifier("secret123", h) and not verifier("autre", h) and not verifier("x", "!")


def test_pages_publiques_et_amorce(client):
    for url in ["/", "/connecteurs", "/demandes", "/carte", "/classement", "/a-propos",
                "/connecteurs/momo-xof-mcp", "/demandes/1", "/devs/sotechdi", "/inscription", "/connexion"]:
        r = client.get(url)
        assert r.status_code == 200, url
    assert "momo-xof-mcp" in client.get("/connecteurs?pays=SN").text
    assert "momo-xof-mcp" not in client.get("/connecteurs?pays=KE").text
    assert client.get("/connecteurs/inexistant").status_code == 404


def test_csrf_obligatoire(client):
    inscrire(client, "awa")
    r = client.post("/demandes/nouvelle", data={"titre": "Une demande sans jeton", "categorie": "sante", "pays": "SN"})
    assert r.status_code == 400


def test_publier_essayer_resoudre(client):
    inscrire(client, "kofi", "GH")
    jeton = csrf(client, "/demandes/nouvelle")
    r = client.post("/demandes/nouvelle", data={"csrf": jeton, "titre": "Connecteur MTN MoMo Ghana",
                                                "categorie": "paiement", "pays": ["GH"]}, follow_redirects=False)
    assert r.status_code == 303
    did = int(r.headers["location"].rsplit("/", 1)[1])

    jeton = csrf(client, f"/connecteurs/nouveau?demande={did}")
    r = client.post("/connecteurs/nouveau", data={
        "csrf": jeton, "demande": did, "nom": "MTN MoMo Ghana", "resume": "Encaisser avec MTN MoMo au Ghana",
        "categorie": "paiement", "type": "sdk", "pays": ["GH", "UEMOA"],
        "depot_url": "https://github.com/exemple/momo-gh"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/connecteurs/mtn-momo-ghana"
    page = client.get("/connecteurs/mtn-momo-ghana").text
    assert "À vérifier" in page and "MIT" in page
    assert "Résolue" in client.get(f"/demandes/{did}").text

    # Un autre dev l'essaie : il devient vivant, puis cassé quand un échec est signalé.
    inscrire(client, "ngozi", "NG")
    jeton = csrf(client, "/connecteurs/mtn-momo-ghana")
    client.post("/connecteurs/mtn-momo-ghana/essai", data={"csrf": jeton, "marche": "oui", "pays": "GH"})
    assert "Vivant" in client.get("/connecteurs/mtn-momo-ghana").text
    jeton = csrf(client, "/connecteurs/mtn-momo-ghana")
    client.post("/connecteurs/mtn-momo-ghana/essai", data={"csrf": jeton, "marche": "non", "pays": "GH",
                                                           "note": "Erreur 401 depuis la nouvelle API"})
    api = client.get("/api/connecteurs/mtn-momo-ghana").json()
    assert api["etat"] == "casse" and "BF" in api["pays"]

    # Rejoindre l'équipe donne le droit de modifier la fiche.
    assert client.get("/connecteurs/mtn-momo-ghana/modifier").status_code == 403
    jeton = csrf(client, "/connecteurs/mtn-momo-ghana")
    client.post("/connecteurs/mtn-momo-ghana/rejoindre", data={"csrf": jeton, "role": "Je corrige l'auth"})
    assert client.get("/connecteurs/mtn-momo-ghana/modifier").status_code == 200

    classement = client.get("/classement").text
    assert "kofi" in classement and "Ghana" in classement


def test_soutien_bascule(client):
    inscrire(client, "fatou", "SN")
    jeton = csrf(client, "/demandes/1")
    client.post("/demandes/1/soutenir", data={"csrf": jeton})
    assert any(d["id"] == 1 and d["soutiens"] == 2 for d in client.get("/api/demandes").json())
    client.post("/demandes/1/soutenir", data={"csrf": jeton})
    assert any(d["id"] == 1 and d["soutiens"] == 1 for d in client.get("/api/demandes").json())


def test_redirection_ouverte_refusee(client):
    client.cookies.clear()
    inscrire(client, "moussa")
    client.cookies.clear()
    jeton = csrf(client, "/connexion")
    r = client.post("/connexion", data={"csrf": jeton, "identifiant": "moussa", "mdp": "motdepasse-solide",
                                        "suite": "//evil.example"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"


def test_markdown_sans_html(client):
    inscrire(client, "ibrahim", "NE")
    jeton = csrf(client, "/demandes/1")
    client.post("/demandes/1/message", data={"csrf": jeton, "texte": "<script>alert(1)</script> [x](javascript:alert(1))"})
    page = client.get("/demandes/1").text
    assert "<script>alert(1)</script>" not in page and 'href="javascript:' not in page


def test_regles_etat():
    c = Connecteur(depot_url="https://github.com/a/b", gh_ci="", gh_archive=False)
    t = maintenant()
    assert module_etat.etat(c, [])["niveau"] == "a-verifier"
    ok = Essai(marche=True, le=t - timedelta(days=3))
    ko = Essai(marche=False, le=t - timedelta(days=1))
    assert module_etat.etat(c, [ok])["niveau"] == "vivant"
    assert module_etat.etat(c, [ok, ko])["niveau"] == "casse"
    vieux = Essai(marche=True, le=t - timedelta(days=200))
    assert module_etat.etat(c, [vieux])["niveau"] == "a-verifier"
    c.gh_ci, c.gh_dernier_push = "success", t - timedelta(days=10)
    assert module_etat.etat(c, [])["niveau"] == "vivant"
    c.gh_archive = True
    assert module_etat.etat(c, [])["niveau"] == "casse"


def test_serveur_mcp(client):
    entetes = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    r = client.post("/mcp", headers=entetes, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "test", "version": "1"}}})
    assert r.status_code == 200, r.text
    r = client.post("/mcp", headers=entetes, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    noms = {t["name"] for t in r.json()["result"]["tools"]}
    assert noms == {"chercher_connecteurs", "demandes_ouvertes"}
    r = client.post("/mcp", headers=entetes, json={
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "chercher_connecteurs", "arguments": {"pays": "BF", "recherche": "cadastre"}}})
    fiches = json.loads(r.json()["result"]["content"][0]["text"])
    assert [f["slug"] for f in fiches] == ["mining-cadastre-mcp"]
    # Notification : pas de réponse. Arguments hors schéma : erreur JSON-RPC.
    assert client.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}).status_code == 202
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                                  "params": {"name": "chercher_connecteurs", "arguments": {"pays": 3}}})
    assert r.json()["error"]["code"] == -32602
    assert client.post("/mcp", content=b"{pas du json").status_code == 400
    assert client.get("/mcp").status_code == 405


def test_releve_github_sans_reseau(monkeypatch):
    """Le relevé réel (pas le faux de la fixture) traduit les réponses de l'API GitHub."""
    import urllib.error
    reponses = {
        "/repos/a/b": {"license": {"spdx_id": "MIT"}, "stargazers_count": 4,
                       "pushed_at": "2026-11-01T10:00:00Z", "archived": False, "default_branch": "main"},
        "/repos/a/b/actions/runs": {"workflow_runs": [{"conclusion": "cancelled"}, {"conclusion": "success"}]},
    }

    def faux_api(chemin, params=None):
        if chemin not in reponses:
            raise urllib.error.HTTPError(chemin, 404, "Not Found", {}, None)
        return reponses[chemin]

    monkeypatch.setattr(module_etat, "_api_github", faux_api)
    c = Connecteur(depot_url="https://github.com/a/b")
    module_etat.relever_github(c)
    assert (c.gh_licence, c.gh_ci, c.gh_etoiles, c.gh_erreur) == ("MIT", "success", 4, "")
    c = Connecteur(depot_url="https://github.com/a/inconnu")
    module_etat.relever_github(c)
    assert c.gh_erreur == "Dépôt introuvable ou privé."
    c = Connecteur(depot_url="https://gitlab.com/a/b")
    module_etat.relever_github(c)
    assert "hors GitHub" in c.gh_erreur


def test_licence_declaree(client):
    # brvm-mcp n'a pas de licence détectable sur GitHub : celle déclarée par l'auteur est affichée.
    fiches = {c["slug"]: c for c in client.get("/api/connecteurs").json()}
    assert fiches["brvm-mcp"]["licence"] == "Commerciale (SOTECHDI)"
    assert "Déclarée par l'auteur" in client.get("/connecteurs/brvm-mcp").text
    c = Connecteur(gh_licence="MIT", licence_declaree="Commerciale")
    assert c.licence == "MIT"  # la licence relevée sur le dépôt prime
