# Architecture — Hôtel Gérard et Francine

Refonte du site de l'hôtel Gérard et Francine (Ambatoloaka, Nosy Be).
Objectifs : SEO maximal, design premium, administration simple pour le propriétaire.

## Stack

| Couche | Technologie |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS — à venir |
| Backend | FastAPI, SQLAlchemy 2 (async), asyncpg, Alembic, Pydantic v2 |
| Base de données | PostgreSQL 18 |
| Qualité | Ruff (lint + format), mypy strict, pytest |
| Déploiement | VPS Contabo, Docker Compose, Nginx, Let's Encrypt — à venir |

## Démarrer

    docker compose up -d                  # PostgreSQL (crée aussi hotel_test au premier démarrage)
    cd backend
    python3 -m venv .venv && source .venv/bin/activate
    make install                          # dépendances de développement
    cp .env.example .env                  # puis générer APP_SECRET_KEY : openssl rand -hex 32
    make migrate                          # schéma de la base de développement
    python -m app.cli create-user --email vous@exemple.com --name "Prénom"
    make run                              # API sur http://127.0.0.1:8000, doc sur /docs
    make check                            # format, lint, types et tests : à lancer avant chaque commit

## Backend — architecture en couches

    backend/app/
    ├── core/          Configuration, sécurité, règles métier pures (prix, statuts, slugs, images)
    ├── db/            Session, base SQLAlchemy, mixins, types partagés
    ├── models/        Modèles ORM (tables)
    ├── schemas/       Schémas Pydantic (contrat de l'API)
    ├── repositories/  Accès aux données uniquement
    ├── services/      Logique métier et transactions
    ├── api/v1/        Routes HTTP, fines
    ├── storage/       Stockage des fichiers (disque local, stockage objet plus tard)
    ├── mail/          Envoi d'emails (console en développement, SMTP en production)
    └── cli.py         Commandes d'administration (comptes, mots de passe, déblocage)

Flux unique : route → service → repository → base de données.

- Une route valide, appelle un service, convertit en schéma. Aucune règle métier.
- Un repository lit et écrit. Aucune règle métier, jamais de commit.
- Un service décide et fait le commit : il voit l'opération complète (unité de travail).
- Les erreurs métier (`core/exceptions.py`) sont traduites en codes HTTP dans `api/errors.py`.
  Un service ne connaît pas HTTP : il lève `NotFoundError`, pas `HTTPException(404)`.
- Les règles complexes sont des fonctions pures dans `core/` (`pricing.py`, `booking.py`,
  `images.py`, `text.py`) : testées en profondeur sans base ni API.

## Modules

| Module | Admin | Public |
|---|---|---|
| Réglages de l'hôtel, 4 langues, réseaux sociaux | propriétaire | `/hotel` |
| Chambres, équipements, photos | propriétaire | `/rooms`, `/rooms/{slug}` |
| Médias : upload, WebP en 3 tailles, textes alternatifs | propriétaire | fichiers `/media/...` |
| Saisons et tarifs | propriétaire | `/rooms/{slug}/quote` |
| Demandes de réservation | propriétaire et réception | `/booking-requests` |
| Avis clients | propriétaire et réception | `/reviews`, `/reviews/summary` |
| Authentification | — | `/auth/login`, `/auth/logout`, `/auth/me` |

Rôles : `owner` (tout), `staff` (réservations et avis). Les accès sont définis par
module dans `api/v1/router.py`, en trois sections : public, propriétaire, propriétaire et réception.

## Décisions métier

**Langues.** fr (par défaut), en, it, de, définies une seule fois dans `core/i18n.py`.
Chaque contenu traduisible a sa table de traductions. Le français est obligatoire ;
une langue absente se replie sur le français, et la réponse le signale (`content_locale`).
Les slugs sont traduits et générés depuis le nom (`core/text.py`).

**Réservations = demandes.** Aucune vérification de disponibilité : toute demande est
acceptée en `pending`, la réception confirme ou propose d'autres dates.
Les règles de l'hôtel (capacité, séjour minimum, tarif manquant) ne bloquent jamais :
elles deviennent des avertissements, visibles par la réception et expliqués au client.
Le prix est figé au moment de la demande. Transitions : `core/booking.py`.

**Tarifs.** Saisons datées (pas récurrentes), sans chevauchement possible (contrainte
d'exclusion PostgreSQL). Prix par nuit : celui de la saison, sinon le prix de base.
On paie les nuits, pas le jour du départ. Montants en `Decimal`, jamais en `float`.

**Avis.** Tout avis attend la modération. 3 avis par IP et par 24 h. L'IP n'est jamais
stockée : seulement une empreinte HMAC (RGPD). Moyenne sur les seuls avis approuvés.

**Emails.** Envoyés en arrière-plan après la réponse ; un échec est journalisé et ne fait
jamais échouer la demande. Texte brut, dans la langue du client.

## Sécurité

- Mots de passe : Argon2 (`pwdlib`). Minimum 12 caractères, jamais égal à l'email.
- Session : JWT en cookie `HttpOnly`, `SameSite=lax`, `Secure` hors développement.
- Connexion : même message pour tous les échecs, hachage factice contre les attaques
  temporelles, blocage après 5 échecs en 15 min par email (20 par IP).
- Uploads : format vérifié par le contenu, EXIF (GPS) supprimé, noms aléatoires,
  taille limitée, chemins protégés contre la traversée de répertoires.
- Formulaires publics : champ piège (honeypot) ; Cloudflare Turnstile à ajouter côté frontend.
- Secrets uniquement dans `.env` (jamais versionné). `SecretStr` pour les mots de passe.

## Règles apprises en route

Chacune correspond à un bug rencontré. À respecter.

1. **Copier un schéma vers un modèle : liste blanche.** `model_dump(include=COLONNES)`,
   jamais `exclude=` : un champ ajouté au schéma ne doit pas pouvoir se glisser en base.
2. **Protéger tout le bloc d'écriture, pas seulement le commit.** Le SQL part au premier
   `flush`, y compris l'autoflush déclenché par une simple requête.
3. **Async : initialiser les collections** (`translations=[]`) à la création d'un objet,
   et charger les relations en `lazy="selectin"`. Un chargement implicite lève `MissingGreenlet`.
4. **Travail bloquant hors de la boucle** : `asyncio.to_thread` pour les fichiers et le
   traitement d'images.
5. **Dans les tests, contrôler le temps** (`hotel_today` remplacé) et remplacer un nom
   là où il est importé, pas là où il est défini.
6. **Aucun `type: ignore` ni `noqa` sans justification écrite.** Si un outil doit être
   réduit au silence partout, c'est le code qui est mal typé.
7. **Caractères typographiques** (`’`, `–`) : les écrire en `\u2019`, `\u2013`, ou reformuler.

## Base de données et migrations

Ordre obligatoire pour toute évolution du schéma :

    modèle → alembic revision --autogenerate → relecture → alembic upgrade head
          → alembic downgrade -1 && alembic upgrade head → make check

- Toujours relire une migration générée. Alembic ne détecte pas les contraintes CHECK
  ajoutées à une table existante : les écrire à la main (voir `add_room_base_price...`).
- Une migration déjà appliquée en production ne se modifie ni ne se supprime jamais.
- Conventions de nommage des contraintes dans `db/base.py` ; types d'énumérations
  (`string_enum`, `enum_check`) dans `db/types.py`.

## Tests

- Base dédiée `hotel_test`, schéma créé par les migrations, vidée avant chaque test.
- Garde-fou : les tests refusent de tourner sur une base dont le nom ne finit pas par `_test`.
- Fixtures communes dans `tests/conftest.py` : `client`, `owner_client`, `make_user`, `media_root`.
- Dépendances remplaçables (`app.dependency_overrides`) : stockage, envoi d'emails.
- Une dépréciation de SQLAlchemy fait échouer les tests.

## Conventions

- Code, noms de variables et de tables en anglais ; documentation et messages en français.
- Commits au format Conventional Commits : `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- Aucun secret dans le dépôt : tout passe par `.env`.
