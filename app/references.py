"""Connecteurs open source existants, écrits par d'autres, référencés au catalogue.

Ils sont publiés sous le compte « veille » : la fiche crédite le propriétaire du
dépôt comme auteur du code, et ce compte n'entre ni dans le classement ni dans
le nombre de devs inscrits. Seuls des dépôts sous licence permissive (MIT,
Apache-2.0), vérifiée le 18/11/2026, figurent ici.
"""
COMPTE_VEILLE = "veille"

_UEMOA = ["BJ", "BF", "CI", "GW", "ML", "NE", "SN", "TG"]
_OHADA = ["BJ", "BF", "CM", "CF", "KM", "CG", "CD", "CI", "GA", "GN", "GW", "GQ",
          "ML", "NE", "SN", "TD", "TG"]

REFERENCES = [
    {
        "slug": "mpesa-mcp", "nom": "mpesa-mcp", "type": "mcp", "langage": "Python",
        "categorie": "paiement", "service": "M-Pesa (Safaricom Daraja) et Africa's Talking",
        "pays": ["KE", "NG", "GH", "TZ", "UG", "RW", "ZA"],
        "resume": "Serveur MCP qui permet à un agent IA de déclencher un paiement M-Pesa, "
                  "suivre une transaction, envoyer des SMS et du crédit d'appel.",
        "description": """Un serveur MCP pour l'Afrique de l'Est : un agent IA peut demander un paiement M-Pesa par STK Push, vérifier son statut, créer un ordre permanent (Ratiba), envoyer des SMS et du crédit d'appel.

**Couverture annoncée** : M-Pesa au Kenya (Daraja v3) ; SMS et crédit d'appel dans une vingtaine de pays via Africa's Talking.

**À savoir** : les envois de SMS sont plafonnés par appel, et chaque envoi réel doit être approuvé par la personne.""",
        "installation": "pip install mpesa-mcp",
        "depot_url": "https://github.com/gabrielmahia/mpesa-mcp",
        "doc_url": "https://pypi.org/project/mpesa-mcp/",
    },
    {
        "slug": "mpesa-node", "nom": "mpesa-node", "type": "sdk", "langage": "JavaScript / TypeScript",
        "categorie": "paiement", "service": "M-Pesa (Safaricom Daraja)", "pays": ["KE"],
        "resume": "Bibliothèque Node.js publiée par Safaricom pour l'API M-Pesa Daraja.",
        "description": """Bibliothèque publiée par **Safaricom** sur son compte GitHub pour appeler l'API REST M-Pesa (Daraja) depuis Node.js.

**À savoir** : le dépôt n'a pas bougé depuis mi-2024. Lisez la documentation Daraja à jour avant de l'utiliser, et dites ici si elle marche encore chez vous.""",
        "installation": "npm i mpesa-node",
        "depot_url": "https://github.com/safaricom/mpesa-node-library",
        "doc_url": "https://developer.safaricom.co.ke/",
    },
    {
        "slug": "africastalking-python", "nom": "africastalking-python", "type": "sdk",
        "langage": "Python", "categorie": "telecoms", "service": "Africa's Talking : SMS, USSD, voix, crédit d'appel",
        "pays": ["KE", "UG", "TZ", "RW", "NG", "MW"],
        "resume": "SDK Python officiel d'Africa's Talking : SMS, USSD, voix et crédit d'appel "
                  "sur les réseaux africains.",
        "description": """Le SDK Python **officiel** d'Africa's Talking, la passerelle qui permet de joindre des utilisateurs sur téléphone simple : SMS, USSD, appels vocaux, crédit d'appel.

**À savoir** : en environnement de test, le nom d'application est toujours `sandbox`. La couverture pays dépend du service : vérifiez-la sur la documentation avant de vous engager.""",
        "installation": "pip install africastalking",
        "depot_url": "https://github.com/AfricasTalkingLtd/africastalking-python",
        "doc_url": "https://developers.africastalking.com",
    },
    {
        "slug": "flutterwave-node-v3", "nom": "flutterwave-node-v3", "type": "sdk",
        "langage": "JavaScript / TypeScript", "categorie": "paiement", "service": "Flutterwave (API v3)",
        "pays": ["NG", "GH", "KE", "UG", "ZA"],
        "resume": "Bibliothèque Node.js officielle de Flutterwave : cartes, mobile money, virements, "
                  "USSD, paiements récurrents.",
        "description": """La bibliothèque Node.js **officielle** de Flutterwave pour son API v3 : encaissements (carte, mobile money, virement, USSD), reversements, abonnements, paiements fractionnés, remboursements, paiement de factures et vérification de compte bancaire.""",
        "installation": "npm install flutterwave-node-v3",
        "depot_url": "https://github.com/Flutterwave/Node-v3",
        "doc_url": "https://developer.flutterwave.com/",
    },
    {
        "slug": "paystack-sdk", "nom": "paystack-sdk", "type": "sdk", "langage": "JavaScript / TypeScript",
        "categorie": "paiement", "service": "Paystack", "pays": ["NG", "GH", "ZA", "KE", "CI"],
        "resume": "SDK TypeScript typé pour l'API Paystack : transactions, virements, clients, "
                  "abonnements, règlements.",
        "description": """SDK communautaire en TypeScript pour Paystack, écrit parce que les bibliothèques existantes étaient non typées ou abandonnées. Il couvre plus de 18 modules de l'API : transactions, virements, clients, abonnements, règlements.""",
        "installation": "npm install paystack-sdk",
        "depot_url": "https://github.com/tekpriest/paystack-node",
        "doc_url": "https://www.npmjs.com/package/paystack-sdk",
    },
    {
        "slug": "cinetpay-php-sdk", "nom": "cinetpay-php-sdk", "type": "sdk", "langage": "PHP",
        "categorie": "paiement", "service": "CinetPay",
        "pays": ["CI", "SN", "BF", "ML", "TG", "BJ", "NE", "CM"],
        "resume": "SDK PHP officiel de CinetPay : paiements web, transferts et consultation du solde.",
        "description": """Le SDK PHP **officiel** de CinetPay, l'agrégateur de paiement d'Afrique francophone : création de paiements web, transferts et consultation du solde.

**À savoir** : CinetPay demande un couple `api_key` / `api_password` **par pays exploité**. Le SDK requiert PHP 8.2 ou plus.""",
        "installation": "composer require cinetpay-dev/cinetpay-php",
        "depot_url": "https://github.com/cinetpay/cinetpay-php-sdk",
        "doc_url": "https://cinetpay.github.io/cinetpay-php-sdk/",
    },
    {
        "slug": "fedapay-php", "nom": "fedapay-php", "type": "sdk", "langage": "PHP",
        "categorie": "paiement", "service": "FedaPay", "pays": ["BJ", "CI", "SN", "TG", "NE"],
        "resume": "Bibliothèque PHP officielle de FedaPay pour encaisser par mobile money et carte.",
        "description": """La bibliothèque PHP **officielle** de FedaPay, passerelle de paiement née au Bénin : mobile money et carte bancaire.

**À savoir** : la version Node.js de FedaPay n'a pas de licence déclarée sur GitHub ; celle-ci est sous MIT.""",
        "installation": "composer require fedapay/fedapay-php",
        "depot_url": "https://github.com/fedapay/fedapay-php",
        "doc_url": "https://docs.fedapay.com",
    },
    {
        "slug": "kkiapay-flutter-sdk", "nom": "kkiapay-flutter-sdk", "type": "sdk", "langage": "Dart",
        "categorie": "paiement", "service": "Kkiapay", "pays": ["BJ"],
        "resume": "SDK Flutter officiel de Kkiapay pour accepter mobile money et carte dans une application.",
        "description": """Le SDK Flutter **officiel** de Kkiapay : il ouvre le parcours de paiement (mobile money ou carte) dans votre application et vous rend la main dans un rappel.

**À savoir** : un compte marchand Kkiapay est nécessaire, même pour tester.""",
        "installation": "flutter pub add kkiapay_flutter_sdk",
        "depot_url": "https://github.com/kkiapay/kkiapay-flutter-sdk",
        "doc_url": "https://docs.kkiapay.me",
    },
    {
        "slug": "orangemoney-go", "nom": "orangemoney-go", "type": "api", "langage": "Go",
        "categorie": "paiement", "service": "Orange Money (API marchand)", "pays": ["CM"],
        "resume": "Client Go non officiel pour l'API Orange Money : jeton, initiation et statut "
                  "d'un paiement marchand.",
        "description": """Client Go **non officiel** pour l'API marchand Orange Money (`omcoreapis`) : obtention du jeton, génération d'un jeton de paiement, notification au client, statut de la transaction.

**À savoir** : les points d'accès Orange Money diffèrent d'un pays à l'autre. Ce client vise l'API utilisée au Cameroun ; dites ici s'il marche ailleurs.""",
        "installation": "go get github.com/NdoleStudio/orangemoney-go",
        "depot_url": "https://github.com/NdoleStudio/orangemoney-go",
    },
    {
        "slug": "momoapi-python", "nom": "momoapi-python", "type": "api", "langage": "Python",
        "categorie": "paiement", "service": "MTN Mobile Money (MoMo API)",
        "pays": ["UG", "GH", "CI", "CM", "BJ", "CG", "ZM", "RW"],
        "resume": "Client Python pour l'API MTN MoMo. Son README annonce l'arrêt de la maintenance "
                  "depuis juillet 2025.",
        "description": """Client Python pour l'API MTN MoMo : encaissements, décaissements et transferts, avec création d'utilisateur en environnement de test.

**Attention** : depuis le 14 juillet 2025, le README annonce que le projet **n'est plus maintenu** (aucun correctif, aucune contribution acceptée). C'est précisément le genre de connecteur dont il faut connaître l'état avant de bâtir dessus : si vous l'utilisez encore, dites-le, et si vous le reprenez, publiez votre version.""",
        "installation": "pip install mtnmomo",
        "depot_url": "https://github.com/sparkplug/momoapi-python",
        "doc_url": "https://momodeveloper.mtn.com/",
    },
    {
        "slug": "ohadakit", "nom": "ohadakit", "type": "sdk", "langage": "JavaScript / TypeScript",
        "categorie": "entreprises", "service": "Plan comptable OHADA / SYSCOHADA", "pays": _OHADA,
        "resume": "SDK TypeScript du plan comptable OHADA / SYSCOHADA, utilisé dans 17 États "
                  "d'Afrique de l'Ouest et centrale.",
        "description": """SDK du **plan comptable SYSCOHADA**, commun aux 17 États de l'OHADA : recherche de comptes, requêtes, comptes personnalisés, traductions, export, sans aucune dépendance.

**À savoir** : il gère le plan de comptes ; les écritures, balances et états financiers restent à votre application.""",
        "installation": "npm install ohadakit",
        "depot_url": "https://github.com/Dahkenangnon/ohadakit",
        "doc_url": "https://ohadakit.claviscore.com",
    },
]
