# MCP for Africa

**La plateforme où les développeurs africains publient, essaient et réparent ensemble
les connecteurs vers les services du continent** : mobile money, données publiques,
administrations, télécoms.

Projet présenté à la **CADEV 2026** (Coupe d'Afrique des Développeurs, Systalink) sur le
thème *« la plateforme d'échange et de collaboration africaine pour les talents tech du continent »*.

## Le problème

Chaque dev africain qui intègre Orange Money, Wave, un registre du commerce ou un
journal officiel en PDF refait le même travail que des centaines d'autres avant lui, et
découvre les mêmes pièges, seul. Les rares connecteurs partagés sur GitHub cassent sans
prévenir quand l'opérateur change son API : personne ne sait lesquels marchent encore.

## Ce que fait MCP for Africa

- **Catalogue de connecteurs** : serveurs MCP, SDK, clients d'API, extracteurs de documents,
  filtrables par pays (54), zone (UEMOA, CEMAC), catégorie et état.
- **État vivant, expliqué** : chaque connecteur est *Vivant*, *À vérifier* ou *Signalé cassé*,
  d'après deux sources indépendantes, et la fiche dit toujours pourquoi :
  - la communauté : « ça marche / ça ne marche pas », par un dev, depuis un pays, à une date ;
  - le dépôt : tests GitHub Actions, dernier commit, archivage, licence (relus automatiquement).
- **Demandes** : les besoins non couverts sont publiés et soutenus (« moi aussi »). Un dev
  prend une demande, publie le connecteur, et tous ceux qui l'attendaient le trouvent.
- **Équipes** : on rejoint l'équipe d'un connecteur pour le maintenir à plusieurs.
- **Carte de couverture** : les 54 pays, avec le nombre de connecteurs et de besoins en attente.
- **Classement** des devs et des pays, qui récompense ce qui aide les autres.
- **Pour les agents IA** : API JSON publique et **serveur MCP** (`/mcp`) : un agent peut
  demander « existe-t-il un connecteur Orange Money qui marche au Burkina ? » et obtenir
  la réponse avec son état.

Les premiers connecteurs publiés sont trois serveurs MCP réels de SOTECHDI (licence MIT) :
mobile money XOF, cadastre minier du Burkina Faso, veille des marchés publics.

## Lancer en local

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt     # Linux/macOS : .venv/bin/pip
.venv/Scripts/python -m uvicorn app.main:app --reload  # http://127.0.0.1:8000
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/verifier_licences.py
```

Sans `DATABASE_URL`, la base est un fichier SQLite local.

## Déploiement (DataCloud Systalink)

Service web Python ou Docker, depuis ce dépôt (`Dockerfile` fourni).

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | URL PostgreSQL (`postgres://…` accepté, le pilote pg8000 est imposé) |
| `DATABASE_SSL` | `1` si la base exige TLS |
| `SECRET_KEY` | Clé de signature des sessions (obligatoire en production) |
| `MFA_ENV` | `production` (cookies sécurisés) |
| `GITHUB_TOKEN` | Facultatif : relève la limite de l'API GitHub (60 → 5000 requêtes/h) |
| `MFA_AMORCE_EMAIL`, `MFA_AMORCE_MDP` | Identifiants du compte d'amorçage `sotechdi` |

Commande de démarrage hors Docker :
`uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'`
Contrôle de santé : `/sante`.

## Technique

FastAPI, Jinja2 (pages rendues côté serveur, aucun framework JavaScript), SQLAlchemy,
PostgreSQL. Sécurité : mots de passe scrypt, jeton CSRF sur tous les formulaires, Markdown
sans HTML brut, redirections internes uniquement, limitation des tentatives de connexion.
La CI exécute les tests et refuse toute dépendance GPL, AGPL ou LGPL.

## Licences

Code sous licence MIT. Dépendances : voir [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

## Usage de l'IA

Voir [DECLARATION_IA.md](DECLARATION_IA.md).
