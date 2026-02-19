.PHONY: help build start stop restart logs status clients add-client remove-client show-qr clean

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
	@echo "  make show-qr NAME=     - Show QR code for client"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean             - Remove all configs (DANGEROUS)"
	@echo ""
	@echo "Configuration:"
	@echo "  Edit .env file with your settings"
	@echo ""

build:
	docker compose build

start:
	docker compose up -d --force-recreate --no-deps
	@echo "Server starting! Use 'make logs' to watch startup"

stop:
	docker compose down

restart:
	docker compose up -d --force-recreate --no-deps
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
	@python3 ./scripts/list-clients.py

add-client:
	@if [ -z "$(NAME)" ]; then \
		echo "ERROR: NAME parameter required. Usage: make add-client NAME=myclient"; \
		exit 1; \
	fi
	@python3 ./scripts/add-client.py "$(NAME)"
	@echo "Restarting server..."
	@docker compose up -d --force-recreate --no-deps

remove-client:
	@if [ -z "$(NAME)" ]; then \
		echo "ERROR: NAME parameter required. Usage: make remove-client NAME=myclient"; \
		exit 1; \
	fi
	@python3 ./scripts/remove-client.py "$(NAME)"
	@echo "Restarting server..."
	@docker compose up -d --force-recreate --no-deps

show-qr:
	@if [ -z "$(NAME)" ]; then \
		echo "ERROR: NAME parameter required. Usage: make show-qr NAME=myclient"; \
		exit 1; \
	fi
	@if [ ! -f ./config/clients/$(NAME)/$(NAME).conf ]; then \
		echo "ERROR: Client '$(NAME)' not found!"; \
		exit 1; \
	fi
	@echo "=== QR Code for client: $(NAME) ==="
	@echo ""
	@docker exec -i amneziawg-server python3 -c 'import qrcode; import sys; data = sys.stdin.read(); qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=2); qr.add_data(data); qr.make(fit=True); qr.print_ascii(invert=True)' < ./config/clients/$(NAME)/$(NAME).conf
	@echo ""
	@echo "Scan this QR code with AmneziaWG mobile app"
	@echo ""

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
