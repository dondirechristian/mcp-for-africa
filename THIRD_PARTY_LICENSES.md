# Licences des composants tiers

Dépendances de l'application en production (`requirements.txt` et leurs dépendances), relevées par `pip-licenses`. Toutes sont permissives : aucune licence à réciprocité (GPL, AGPL, LGPL, MPL, EPL…). La CI le vérifie à chaque envoi (`scripts/verifier_licences.py`).

| Name              | Version | License      |
|-------------------|---------|--------------|
| Jinja2            | 3.1.6   | BSD License  |
| MarkupSafe        | 3.0.4   | BSD-3-Clause |
| SQLAlchemy        | 2.1.8   | MIT          |
| annotated-doc     | 0.0.6   | MIT          |
| annotated-types   | 0.8.0   | MIT          |
| anyio             | 4.16.0  | MIT          |
| asn1crypto        | 1.5.1   | MIT License  |
| click             | 8.5.1   | BSD-3-Clause |
| fastapi           | 0.162.7 | MIT          |
| h11               | 0.16.0  | MIT License  |
| idna              | 3.20    | BSD-3-Clause |
| itsdangerous      | 2.2.0   | BSD License  |
| markdown-it-py    | 4.3.0   | MIT License  |
| mdurl             | 0.1.2   | MIT License  |
| opentelemetry-api | 1.45.2  | Apache-2.0   |
| pg8000            | 1.31.6  | BSD License  |
| pydantic          | 2.14.3  | MIT          |
| pydantic_core     | 2.50.4  | MIT          |
| python-dateutil   | 4.0.0   | BSD-3-Clause |
| python-multipart  | 0.0.33  | Apache-2.0   |
| scramp            | 1.5.0   | MIT-0        |
| starlette         | 1.10.0  | BSD-3-Clause |
| typing-inspection | 0.4.5   | MIT          |
| typing_extensions | 4.16.0  | PSF-2.0      |
| tzdata            | 2026.6  | Apache-2.0   |
| uvicorn           | 0.54.0  | BSD-3-Clause |

## Autres éléments

| Élément | Licence |
|---|---|
| Police `app/static/TwemojiCountryFlags.woff2` (drapeaux) : country-flag-emoji-polyfill | MIT |
| Dessins des drapeaux : Twemoji, © Twitter, Inc. et contributeurs | CC-BY 4.0 (attribution) |
| Image Docker de base `python:3.12-slim` (exécution, non distribuée avec le code) | PSF-2.0 et licences Debian |

Outils de test uniquement (non embarqués) : pytest (MIT), httpx (BSD-3-Clause), pip-licenses (MIT).
