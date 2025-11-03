.PHONY: help build start stop restart logs status clients add-client remove-client clean

help:
	@echo "AmneziaWG Server Management"
	@echo "============================"
	@echo ""
	@echo "Setup:"
	@echo "  make build             - Build Docker image"
	@echo "  make start             - Start server (auto-generates config)"
	@echo ""
	@echo "Management:"
	@echo "  make stop              - Stop server"
	@echo "  make restart           - Restart server"
	@echo "  make logs              - View server logs"
	@echo "  make status            - Show server status and peers"
	@echo ""
	@echo "Clients:"
	@echo "  make clients           - List all clients"
	@echo "  make add-client NAME=  - Add new client"
	@echo "  make remove-client NAME= - Remove client"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean             - Remove all configs (DANGEROUS)"
	@echo ""
	@echo "Configuration:"
	@echo "  Edit docker compose.yml environment section"
	@echo ""

build:
	docker compose build

start:
	docker compose up -d
	@echo "Server starting! Use 'make logs' to watch startup"

stop:
	docker compose down

restart:
	docker compose restart
	@echo "Server restarted!"

logs:
	docker compose logs -f

status:
	@echo "Container status:"
	@docker compose ps
	@echo ""
	@echo "Interface status:"
	@docker exec amneziawg-server awg show 2>/dev/null || echo "Server not running"

clients:
	@./scripts/list-clients.sh

add-client:
	@if [ -z "$(NAME)" ]; then \
		echo "ERROR: NAME parameter required. Usage: make add-client NAME=myclient"; \
		exit 1; \
	fi
	@./scripts/add-client.sh "$(NAME)"
	@echo ""
	@echo "Client added! Don't forget to restart:"
	@echo "  make restart"

remove-client:
	@if [ -z "$(NAME)" ]; then \
		echo "ERROR: NAME parameter required. Usage: make remove-client NAME=myclient"; \
		exit 1; \
	fi
	@./scripts/remove-client.sh "$(NAME)"
	@echo ""
	@echo "Client removed! Don't forget to restart:"
	@echo "  make restart"

clean:
	@echo "WARNING: This will remove ALL configs including server keys!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -rf config/*; \
		echo "Cleaned! Run 'make start' to regenerate."; \
	else \
		echo "Aborted."; \
	fi
