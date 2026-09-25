# Commandes du backend. Usage : make <cible>   (make help pour la liste)
.RECIPEPREFIX = >
.DEFAULT_GOAL := help
.PHONY: help install run migrate format lint typecheck test check

help: ## Affiche cette aide
> @grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-10s %s\n", $$1, $$2}'

install: ## Installe les dépendances de développement
> pip install -r requirements-dev.txt

run: ## Lance l'API en mode développement
> uvicorn app.main:app --reload

migrate: ## Applique les migrations de la base
> alembic upgrade head

format: ## Formate le code
> ruff format .

lint: ## Vérifie le code et corrige ce qui peut l'être
> ruff check . --fix

typecheck: ## Vérifie les types
> mypy app tests

test: ## Lance les tests
> pytest

check: format lint typecheck test ## Lance toutes les vérifications, dans l'ordre
