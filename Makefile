# Convenience wrapper around docker compose. (Windows users without `make` can run
# the underlying `docker compose ...` commands directly — see the README.)
.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help build up down clean logs ps dbt-debug test

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n",$$1,$$2}'

build:  ## Build the images
	$(COMPOSE) build

up:  ## Start the full stack (detached)
	$(COMPOSE) up -d

down:  ## Stop the stack (keep data volumes)
	$(COMPOSE) down

clean:  ## Stop and remove volumes (full reset)
	$(COMPOSE) down -v

logs:  ## Follow logs for all services
	$(COMPOSE) logs -f

ps:  ## Show service status
	$(COMPOSE) ps

dbt-debug:  ## Run `dbt debug` against the warehouse (on-demand dbt service)
	$(COMPOSE) run --rm dbt debug --project-dir /opt/airflow/dbt/ebury --profiles-dir /opt/airflow/dbt/ebury

test:  ## Run DAG import unit tests inside the Airflow image
	$(COMPOSE) run --rm airflow-scheduler bash -c "cd /opt/airflow && pytest tests -q"
