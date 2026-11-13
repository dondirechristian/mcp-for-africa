# MCP for Africa : comment ça marche, pour le défendre devant le jury

Le jury note la « maîtrise par l'équipe de la solution livrée, y compris des parties produites
à l'aide de l'IA, et sa capacité à l'expliquer ». Ce document fait le tour du code en
partant des questions qu'on vous posera. Chaque fichier cité est court : lisez-le une fois.

## 1. Vue d'ensemble

```
Navigateur ──► FastAPI (app/main.py) ──► SQLAlchemy (app/db.py) ──► PostgreSQL (DataCloud)
                   │                         ▲
                   ├─ gabarits Jinja2 ───────┘   pages HTML rendues côté serveur
                   ├─ /api/...  JSON public
                   ├─ /mcp      serveur MCP (app/agents.py)
                   └─ relecture GitHub (app/etat.py) ──► api.github.com
```

- **Pas de framework JavaScript.** Les pages sont produites côté serveur : elles s'affichent
  vite sur une connexion mobile lente, et il n'y a qu'un seul programme à maintenir.
- **Une seule application, une seule base.** Le service web DataCloud lance l'image Docker ;
  la base PostgreSQL gérée de DataCloud garde les données.

## 2. Les fichiers

| Fichier | Rôle |
|---|---|
| `app/main.py` | Toutes les pages et actions (routes), la session, les comptes, l'API JSON |
| `app/db.py` | Les 7 tables : devs, connecteurs, essais, contributeurs, demandes, soutiens, messages |
| `app/etat.py` | La relecture GitHub et le calcul de l'état d'un connecteur |
| `app/agents.py` | Le serveur MCP (protocole JSON-RPC écrit à la main) |
| `app/securite.py` | Mots de passe, jeton anti-CSRF, limitation des tentatives |
| `app/referentiel.py` | Les 54 pays, les zones UEMOA/CEMAC, les catégories |
| `app/amorce.py` | Le contenu de départ (4 connecteurs, 4 demandes), sur base vide uniquement |
| `app/templates/` | Les pages HTML ; `_macros.html` contient les morceaux réutilisés |
| `tests/` | 10 tests qui rejouent les parcours complets |

## 3. Le cœur : l'état d'un connecteur (`app/etat.py`, fonction `etat`)

Un connecteur est :

- **Signalé cassé** si le dépôt est archivé, OU si ses tests GitHub échouent, OU si le
  dernier essai d'un développeur (sur 60 jours) est un échec plus récent que le dernier succès ;
- sinon **Vivant** si un développeur a confirmé qu'il marche dans les 60 derniers jours, OU si
  ses tests passent et que le code a bougé dans les 6 derniers mois ;
- sinon **À vérifier**.

La fonction renvoie toujours la liste des raisons : l'interface les affiche, l'agent IA les
reçoit. *Pourquoi deux sources ?* Les tests disent si le code est sain ; seul un humain, dans
son pays, peut dire si l'opérateur a changé son API la semaine dernière.

*Pourquoi un échec récent l'emporte-t-il ?* Parce que pour un développeur, un faux « vivant »
coûte une journée de débogage ; un faux « cassé » coûte un essai.

**La relecture GitHub** (`relever_github`) appelle deux adresses de l'API GitHub : la fiche
du dépôt (licence, étoiles, dernier commit, archivage) et les derniers lancements de tests.
Elle ne lève jamais d'erreur : en cas de problème, le message est stocké et affiché. Elle est
relancée au plus toutes les 6 heures, en arrière-plan, quand quelqu'un ouvre la fiche.

## 4. Le serveur MCP (`app/agents.py`)

MCP (Model Context Protocol) est le standard qui permet à un assistant IA (Claude, Cursor,
VS Code…) d'appeler des outils. Le transport est du JSON-RPC 2.0 sur une requête HTTP POST.

Notre serveur répond à 4 méthodes : `initialize` (présentation), `ping`, `tools/list` (les
2 outils et leurs paramètres) et `tools/call` (exécuter un outil). Les notifications (messages
sans `id`) reçoivent un « 202 » sans contenu, comme le prévoit la spécification.

*Pourquoi ne pas utiliser le SDK officiel ?* Il entraîne une vingtaine de dépendances, dont une
sous licence MPL-2.0 (à réciprocité), ce que le règlement exclut. Pour deux outils en
lecture seule, 150 lignes suffisent, et il a été vérifié avec le client officiel du SDK.

## 5. Sécurité (critère « qualité technique »)

- **Mots de passe** : jamais stockés en clair ; hachage scrypt avec un sel aléatoire par compte
  (`securite.py`), comparaison en temps constant.
- **CSRF** : chaque formulaire porte un jeton propre à la session ; une requête sans le bon
  jeton est refusée (test `test_csrf_obligatoire`).
- **Contenu des utilisateurs** : le Markdown est rendu sans HTML brut, et les liens
  `javascript:` sont neutralisés (test `test_markdown_sans_html`). Jinja2 échappe tout le reste.
- **Redirections** : après connexion, on ne redirige que vers une adresse du site
  (test `test_redirection_ouverte_refusee`).
- **Abus** : 8 tentatives de connexion par 10 minutes, 40 actions par 10 minutes et par compte.
- **Session** : cookie signé, `HttpOnly`, `SameSite=Lax`, `Secure` en production. La clé de
  signature (`SECRET_KEY`) est une variable d'environnement, jamais dans le code.
- **Base** : requêtes construites par SQLAlchemy, donc paramétrées (pas d'injection SQL).

## 6. Licences (conformité, article 6)

- `requirements.txt` ne contient que des licences permissives.
- `psycopg` (LGPL) écarté au profit de `pg8000` (BSD) : voir `app/db.py`, fonction `url_base`.
- La CI (`.github/workflows/ci.yml`) installe uniquement les dépendances de production et
  lance `scripts/verifier_licences.py`, qui échoue sur toute licence à réciprocité.

## 7. Questions probables du jury

**« En quoi est-ce une plateforme d'échange et de collaboration ? »** On y échange du code
(connecteurs), des retours d'expérience datés (essais), des besoins (demandes), et on
collabore : équipes par connecteur, demandes prises en charge et résolues, discussions.

**« Qu'est-ce qui la distingue d'un forum ou de GitHub ? »** GitHub héberge le code mais ne
dit pas s'il marche encore au Sénégal aujourd'hui, ni ce qui manque au Niger. Un forum perd
l'information dans des fils. Ici, chaque connecteur porte un état vérifiable et daté, et la
carte montre où le continent manque d'outils.

**« Pourquoi l'IA dans le nom ? »** Les développeurs codent de plus en plus avec des agents IA.
Un agent ne sait pas quel connecteur africain existe ni s'il marche. MCP for Africa le lui dit
par le protocole standard des agents, et les connecteurs de type « serveur MCP » permettent à
ces agents d'utiliser directement les services africains.

**« Comment ça tient la charge ? »** Pages rendues côté serveur, requêtes SQL indexées sur les
colonnes filtrées (slug, catégorie, pays), relecture GitHub en arrière-plan et limitée à une
fois toutes les 6 h par connecteur. Pour monter en charge : plusieurs instances derrière le
répartiteur DataCloud (l'application ne garde rien en mémoire, sauf le compteur anti-abus) et
un `GITHUB_TOKEN` (5 000 appels/h au lieu de 60).

**« Comment empêcher les faux essais ? »** Un essai par compte et par connecteur (contrainte
d'unicité en base), comptes limités en débit, et un échec doit être expliqué en une phrase.
Étape suivante : pondérer les essais par l'ancienneté et la réputation du compte.

**« Qu'est-ce que l'IA a fait, et qu'avez-vous fait ? »** Voir `DECLARATION_IA.md`. Soyez
précis : le concept, les choix de produit et les contenus sont de l'équipe ; l'assistant a
écrit l'essentiel du code, que l'équipe a relu, testé et sait expliquer avec ce document.

## 8. Démonstration en 2 minutes

1. Accueil : le problème (la même intégration Orange Money réécrite partout), les chiffres.
2. Carte : 54 pays, les trous sont visibles.
3. Fiche `momo-xof-mcp` : état « Vivant » et sa raison, les pièges documentés, l'installation.
4. Se connecter avec un second compte, déclarer « ça ne marche pas » avec une phrase :
   l'état passe à « Signalé cassé » pour tout le monde.
5. Demandes : soutenir « Connecteur Wave », cliquer « Je m'en occupe ».
6. Page « Pour les agents IA » : brancher l'adresse `/mcp` dans Claude ou Cursor et demander
   « existe-t-il un connecteur de paiement qui marche au Burkina ? ».
