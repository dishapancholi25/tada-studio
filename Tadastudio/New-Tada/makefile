# Azure Container Registry Configuration
# REGISTRY := exposeaicrdevaue02.azurecr.io
REGISTRY := synaicraue.azurecr.io


# Image names
BACKEND_IMAGE := backend:latest
FRONTEND_IMAGE := frontend:latest
NGINX_IMAGE := nginx-auth:latest

# BACKEND_REMOTE := $(REGISTRY)/explainstudio_be:latest
# FRONTEND_REMOTE := $(REGISTRY)/explainstudio_fe:latest
# NGINX_REMOTE := $(REGISTRY)/nginx-auth:latest

BACKEND_REMOTE := $(REGISTRY)/agenticstudio_be:latest
FRONTEND_REMOTE := $(REGISTRY)/agenticstudio_fe:latest
NGINX_REMOTE := $(REGISTRY)/nginx-auth:latest

# Target platform (Azure runs linux/amd64)
PLATFORM := linux/amd64

# Colors for output
GREEN := \033[0;32m
BLUE := \033[0;34m
YELLOW := \033[1;33m
NC := \033[0m

ifeq ($(OS),Windows_NT)
  DOCKER ?= docker.exe
else
  DOCKER ?= docker
endif

.PHONY: help backend frontend nginx all all-parallel clean login restart

# Default target
help:
	@echo "$(BLUE)Agentic Studio Deployment Makefile$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@echo "  make backend         - Build and push backend only"
	@echo "  make frontend        - Build and push frontend only"
	@echo "  make nginx           - Build and push nginx only"
	@echo "  make all             - Build and push all components sequentially"
	@echo "  make all-parallel    - Build and push all components in parallel (fastest)"
	@echo "  make login           - Login to Azure Container Registry"
	@echo "  make restart         - Rebuild and restart dev docker compose stack"
	@echo "  make clean           - Remove local Docker images"
	@echo ""
	@echo "$(YELLOW)Quick Examples:$(NC)"
	@echo "  make frontend        # When you only changed frontend code"
	@echo "  make backend         # When you only changed backend code"
	@echo "  make all-parallel    # Full deployment (fastest)"

# Backend deployment
backend:
	@echo "$(BLUE)[Backend]$(NC) Building..."
	docker build --platform $(PLATFORM) -t $(BACKEND_IMAGE) -f backend/Dockerfile backend/
	@echo "$(BLUE)[Backend]$(NC) Tagging..."
	docker tag $(BACKEND_IMAGE) $(BACKEND_REMOTE)
	@echo "$(BLUE)[Backend]$(NC) Pushing to registry..."
	docker push $(BACKEND_REMOTE)
	@echo "$(GREEN)[Backend]$(NC) ✓ Deployed successfully!"

# Frontend deployment
frontend:
	@echo "$(BLUE)[Frontend]$(NC) Building..."
	docker build --platform $(PLATFORM) -t $(FRONTEND_IMAGE) ./frontend
	@echo "$(BLUE)[Frontend]$(NC) Tagging..."
	docker tag $(FRONTEND_IMAGE) $(FRONTEND_REMOTE)
	@echo "$(BLUE)[Frontend]$(NC) Pushing to registry..."
	docker push $(FRONTEND_REMOTE)
	@echo "$(GREEN)[Frontend]$(NC) ✓ Deployed successfully!"

# Nginx deployment
nginx:
	@echo "$(BLUE)[Nginx]$(NC) Building..."
	docker build --platform $(PLATFORM) -f Dockerfile.nginx -t $(NGINX_IMAGE) .
	@echo "$(BLUE)[Nginx]$(NC) Tagging..."
	docker tag $(NGINX_IMAGE) $(NGINX_REMOTE)
	@echo "$(BLUE)[Nginx]$(NC) Pushing to registry..."
	docker push $(NGINX_REMOTE)
	@echo "$(GREEN)[Nginx]$(NC) ✓ Deployed successfully!"


# Sequential deployment of all components
all: backend frontend nginx
	@echo "$(GREEN)✓ All components deployed successfully!$(NC)"

# Parallel deployment (fastest option)
all-parallel:
	@echo "$(BLUE)Starting parallel deployment...$(NC)"
	@$(MAKE) -j3 backend frontend nginx
	@echo "$(GREEN)✓ All components deployed successfully!$(NC)"

# Login to Azure Container Registry
login:
	@echo "$(BLUE)Logging in to Azure Container Registry...$(NC)"
	az acr login --name exposeaicrdevaue02
	@echo "$(GREEN)✓ Login successful!$(NC)"

# Clean up local images
clean:
	@echo "$(YELLOW)Removing local Docker images...$(NC)"
	-docker rmi $(BACKEND_IMAGE) $(FRONTEND_IMAGE) $(NGINX_IMAGE) 2>/dev/null
	-docker rmi $(BACKEND_REMOTE) $(FRONTEND_REMOTE) $(NGINX_REMOTE) 2>/dev/null
	@echo "$(GREEN)✓ Cleanup complete!$(NC)"

# Build without push (for testing)
build-backend:
	@echo "$(BLUE)[Backend]$(NC) Building (no push)..."
	docker build --platform $(PLATFORM) -t $(BACKEND_IMAGE) -f backend/Dockerfile backend/

build-frontend:
	@echo "$(BLUE)[Frontend]$(NC) Building (no push)..."
	docker build --platform $(PLATFORM) -t $(FRONTEND_IMAGE) ./frontend

build-nginx:
	@echo "$(BLUE)[Nginx]$(NC) Building (no push)..."
	docker build --platform $(PLATFORM) -f Dockerfile.nginx -t $(NGINX_IMAGE) .

build-all: build-backend build-frontend build-nginx
	@echo "$(GREEN)✓ All components built (not pushed)$(NC)"

# Restart dev docker compose stack (rebuild and restart)
restart:
	@echo "$(BLUE)Stopping dev containers...$(NC)"
	docker compose -f docker-compose.dev.yml down
	@echo "$(BLUE)Rebuilding and starting dev containers...$(NC)"
	docker compose -f docker-compose.dev.yml up -d --build
	@echo "$(GREEN)✓ Dev stack restarted successfully!$(NC)"
