# Architecture — Hôtel Gérard et Francine

Refonte du site de l'hôtel Gérard et Francine (Ambatoloaka, Nosy Be).
Objectifs : SEO maximal, design premium, administration simple pour le propriétaire.

## Stack

| Couche | Technologie |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Base de données | PostgreSQL |
| Déploiement | VPS Contabo, Docker Compose, Nginx, Let's Encrypt |

## Structure du monorepo

    gerard-et-francine-hotel/
    ├── frontend/            Application Next.js (site public + /admin)
    ├── backend/             API FastAPI
    ├── docs/                Documentation technique
    ├── docker-compose.yml
    └── .env.example

## Backend — architecture en couches

    backend/app/
    ├── core/          Configuration, sécurité (JWT), logging
    ├── db/            Session et base SQLAlchemy
    ├── models/        Modèles ORM (tables)
    ├── schemas/       Schémas Pydantic (entrée/sortie API)
    ├── repositories/  Accès aux données uniquement
    ├── services/      Logique métier
    └── api/v1/        Routes HTTP

Règles :
- Flux unique : route → service → repository → base de données.
- Une route ne contient aucune logique métier ; elle valide et délègue.
- Un repository ne contient aucune règle métier ; il lit et écrit.
- Les modèles ORM ne sortent jamais de l'API : on renvoie toujours un schéma Pydantic.
- Toute modification du schéma de base passe par une migration Alembic.

## Modules métier

| Module | Rôle |
|---|---|
| settings | Infos de l'hôtel : nom, adresse, email, téléphone, WhatsApp, réseaux sociaux, horaires |
| rooms | Types de chambres, descriptions, équipements, capacité, photos |
| rates | Tarifs par saison et par type de chambre |
| bookings | Demandes de réservation, disponibilités, statuts |
| reviews | Avis clients avec modération |
| pages | Contenus éditables des pages (activités, Ambatoloaka, tourisme durable…) |
| media | Upload et gestion des images |
| payments | Réservé — paiement en ligne prévu dans une phase ultérieure |

## Internationalisation

- Langues : fr (défaut), en, it, de.
- URL préfixées par la langue avec slugs traduits : /fr/chambres, /en/rooms, /it/camere, /de/zimmer.
- Chaque contenu traduisible a sa table de traductions (ex. room + room_translation).
- Ajouter une langue ne doit nécessiter aucune modification de structure.

## Réservations

- Phase 1 : demande de réservation sans paiement, confirmée par l'hôtel.
- Statuts : pending → confirmed | cancelled → completed.
- Champ payment_status présent dès le départ (valeur par défaut : not_required).
- Le module payments expose une interface ; un fournisseur (Stripe, PayPal, MVola…)
  pourra être branché plus tard sans modifier le module bookings.

## Avis clients

- Ouverts à tous les visiteurs.
- Tout avis est créé en statut pending ; seul l'admin peut le passer en approved ou rejected.
- Anti-spam : Cloudflare Turnstile, champ honeypot, limitation de débit par IP.
- Seuls les avis approuvés sont publiés et comptés dans la note (JSON-LD AggregateRating).

## SEO

- Pages publiques en rendu statique (SSG/ISR).
- Revalidation à la demande : une modification dans l'admin régénère les pages concernées.
- Metadata API Next.js, sitemap.xml et robots.txt générés, balises hreflang.
- Données structurées JSON-LD : Hotel, HotelRoom, Offer, AggregateRating.
- Images optimisées via next/image.

## Administration

- Accessible sur /admin, dans l'application Next.js.
- Authentification JWT en cookie httpOnly.
- Interface pensée pour un utilisateur non technique.

## Conventions

- Code, noms de variables et de tables en anglais ; documentation en français.
- Commits au format Conventional Commits : feat:, fix:, docs:, refactor:, chore:…
- Branche principale : main. Développement sur des branches feat/…, fix/…
- Aucun secret dans le dépôt : tout passe par les fichiers .env (non versionnés).
