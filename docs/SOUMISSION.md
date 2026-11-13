# Dossier de soumission — CADEV 2026

Textes prêts à copier dans le formulaire de soumission. Les passages entre [crochets] sont à compléter.

## Identité du projet

- **Nom** : MCP for Africa
- **Équipe** : [nom de l'équipe] — représentant : Christian Aristide Dondire — pays de représentation : Burkina Faso
- **Démo en ligne** : [URL DataCloud]
- **Code source** : https://github.com/dondirechristian/mcp-for-africa
- **Produit DataCloud utilisé** : [ex. service web Starter + base PostgreSQL], acquis avec la remise CADEV

## Résumé (une phrase)

MCP for Africa est la plateforme où les développeurs africains publient, essaient et réparent ensemble les connecteurs vers les services du continent (mobile money, données publiques, administrations), avec pour chacun un état « vivant / à vérifier / cassé » tenu par la communauté et lisible par les agents IA.

## Description

Chaque développeur africain qui intègre Orange Money, Wave, un registre du commerce ou un journal officiel en PDF refait seul le travail de centaines d'autres, et retombe dans les mêmes pièges. Les rares connecteurs partagés cassent sans prévenir quand l'opérateur change son API, et personne ne sait lesquels marchent encore.

MCP for Africa réunit ces connecteurs en un seul endroit et en fait un travail collectif :

- **un catalogue** filtrable par pays (les 54), zone (UEMOA, CEMAC), catégorie et état ;
- **un état vivant et expliqué** pour chaque connecteur, calculé à partir de deux sources indépendantes : les essais des développeurs (« ça marche / ça ne marche pas », depuis tel pays, à telle date) et la relecture automatique du dépôt GitHub (tests, licence, activité) ;
- **des demandes** : les besoins non couverts sont publiés et soutenus ; un développeur en prend un, publie le connecteur, et tous ceux qui l'attendaient le trouvent ;
- **des équipes** par connecteur, des fils de discussion, une **carte de couverture** du continent et un **classement** des développeurs et des pays qui récompense l'entraide ;
- **une ouverture aux agents IA** : API JSON publique et serveur MCP intégré, pour qu'un assistant de code puisse répondre « existe-t-il un connecteur Orange Money qui marche au Burkina ? ».

## Déclaration des composants tiers et de leurs licences

Toutes les dépendances sont sous licence permissive ; aucune n'est sous licence à réciprocité (GPL, AGPL, LGPL, ni MPL, EPL…). Une vérification automatique tourne à chaque envoi de code (`scripts/verifier_licences.py`, job « licences » de la CI). Liste complète : `THIRD_PARTY_LICENSES.md`.

Principaux composants : FastAPI (MIT), Starlette (BSD-3), Uvicorn (BSD-3), Jinja2 (BSD-3), SQLAlchemy (MIT), pg8000 (BSD-3), Pydantic (MIT), markdown-it-py (MIT), itsdangerous (BSD-3), python-multipart (Apache-2.0). Police des drapeaux : country-flag-emoji-polyfill (MIT), dessins Twemoji (CC-BY 4.0).

Choix faits pour respecter le règlement : le pilote PostgreSQL habituel (psycopg, LGPL) a été écarté au profit de pg8000 (BSD) ; le protocole MCP est implémenté directement, sans SDK, pour éviter une dépendance indirecte sous MPL-2.0.

## Éléments antérieurs au concours

Aucune ligne de code antérieure au concours n'est intégrée à la plateforme : tout le dépôt `mcp-for-africa` a été créé pendant la durée du concours.

La plateforme **référence** comme premiers contenus de son catalogue quatre projets appartenant au représentant de l'équipe et antérieurs au concours : `brvm-mcp`, `momo-xof-mcp`, `mining-cadastre-mcp` et `veille-marches-publics-bf`. Ce sont des fiches du catalogue (nom, description, lien vers le dépôt), au même titre que les connecteurs que publieront les utilisateurs ; leur code ne fait pas partie de la solution soumise.

## Déclaration d'usage de l'intelligence artificielle

- **Outil** : Claude (Anthropic), modèle Claude Opus, utilisé dans Claude Code comme assistant de programmation.
- **Parties concernées** : architecture et schéma de données, code Python (`app/`), gabarits HTML et feuille de style, tests automatisés, CI, Dockerfile, script de vérification des licences, documentation et textes de l'interface.
- **Part de l'équipe** : choix du sujet et du concept (connecteurs africains à état vivant, ouverture aux agents IA), spécifications, contenus d'origine, relecture, essais, déploiement sur DataCloud.
- **Traçabilité** : les commits produits avec l'assistant portent la mention `Co-Authored-By: Claude`.
- La plateforme elle-même n'appelle aucun modèle d'IA et n'envoie aucune donnée d'utilisateur à un service d'IA.

## Déclaration de titularité (à faire par chaque membre)

« Je déclare que le projet MCP for Africa a été créé en dehors de toute mission confiée par un employeur, un client ou un établissement d'enseignement susceptible d'en revendiquer les droits. »
