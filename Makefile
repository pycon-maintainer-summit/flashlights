# The instance from the image, locally. `make` lists the targets.
.DEFAULT_GOAL := help
COMPOSE = docker compose
MANAGE = $(COMPOSE) run --rm web python manage.py

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

build: ## Build the image from the pinned core
	$(COMPOSE) build web

seed: ## Migrate a fresh database and load the Maintainer Summit preset
	$(MANAGE) createcachetable
	$(MANAGE) migrate
	$(MANAGE) set_site_domain 127.0.0.1:8007
	$(MANAGE) load_preset /community/presets/summit

up: ## Serve on http://127.0.0.1:8007/ (emails at http://127.0.0.1:9007/)
	$(COMPOSE) up -d web worker maildev

logs: ## Follow the web and worker logs
	$(COMPOSE) logs -f web worker

lint: ## black, isort and flake8 (pip install -r requirements-dev.txt)
	black --check . && isort --check-only . && flake8

test: ## Run the app's tests inside the image (pytest is installed into the container first)
	$(COMPOSE) run --rm web sh -c "pip install -q pytest==8.3.5 pytest-django==4.8.0 && python -m pytest /community/tests -p no:cacheprovider"

down: ## Stop everything and drop the database
	$(COMPOSE) down -v
