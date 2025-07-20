# Terraform Makefile for Entropy-Playground

.PHONY: help init plan-dev plan-prod apply-dev apply-prod destroy-dev destroy-prod fmt validate clean deploy-ecs rollback-ecs monitor-ecs

# Default environment
ENV ?= dev

help:
	@echo "Available targets:"
	@echo "  init        - Initialize Terraform"
	@echo "  plan-dev    - Plan changes for development environment"
	@echo "  plan-prod   - Plan changes for production environment"
	@echo "  apply-dev   - Apply changes to development environment"
	@echo "  apply-prod  - Apply changes to production environment"
	@echo "  destroy-dev - Destroy development environment"
	@echo "  destroy-prod- Destroy production environment"
	@echo "  fmt         - Format Terraform files"
	@echo "  validate    - Validate Terraform configuration"
	@echo "  clean       - Clean Terraform files"
	@echo ""
	@echo "ECS-specific targets:"
	@echo "  deploy-ecs  - Deploy new version to ECS (ENV=dev|prod TAG=version)"
	@echo "  rollback-ecs- Rollback ECS to previous version"
	@echo "  monitor-ecs - Monitor ECS services and tasks"

init:
	@if [ -f backend.conf ]; then \
		terraform init -backend-config=backend.conf; \
	else \
		terraform init; \
	fi

plan-dev: init
	terraform plan -var-file=environments/dev/terraform.tfvars -out=dev.tfplan

plan-prod: init
	terraform plan -var-file=environments/prod/terraform.tfvars -out=prod.tfplan

apply-dev: plan-dev
	terraform apply dev.tfplan
	@rm -f dev.tfplan

apply-prod: plan-prod
	@echo "WARNING: You are about to apply changes to PRODUCTION!"
	@echo "Press Ctrl+C to cancel, or Enter to continue."
	@read confirm
	terraform apply prod.tfplan
	@rm -f prod.tfplan

destroy-dev: init
	@echo "WARNING: This will destroy all development infrastructure!"
	@echo "Press Ctrl+C to cancel, or Enter to continue."
	@read confirm
	terraform destroy -var-file=environments/dev/terraform.tfvars

destroy-prod: init
	@echo "DANGER: This will destroy all PRODUCTION infrastructure!"
	@echo "Type 'destroy production' to confirm:"
	@read confirm; \
	if [ "$$confirm" = "destroy production" ]; then \
		terraform destroy -var-file=environments/prod/terraform.tfvars; \
	else \
		echo "Destruction cancelled."; \
	fi

fmt:
	terraform fmt -recursive .

validate: init
	terraform validate

clean:
	rm -rf .terraform/
	rm -f *.tfplan
	rm -f .terraform.lock.hcl

# Environment-specific shortcuts
dev-plan: plan-dev
dev-apply: apply-dev
dev-destroy: destroy-dev

prod-plan: plan-prod
prod-apply: apply-prod
prod-destroy: destroy-prod

# ECS deployment targets
deploy-ecs:
	@if [ -z "$(TAG)" ]; then \
		echo "Error: TAG is required. Usage: make deploy-ecs ENV=dev TAG=v1.0.0"; \
		exit 1; \
	fi
	@echo "Deploying to ECS $(ENV) environment with tag $(TAG)..."
	./scripts/ecs/deploy.sh -e $(ENV) -t $(TAG) -w

rollback-ecs:
	@echo "Rolling back ECS $(ENV) environment..."
	./scripts/ecs/rollback.sh -e $(ENV)

monitor-ecs:
	@echo "Monitoring ECS $(ENV) environment..."
	./scripts/ecs/monitor.sh -e $(ENV) -t -l -m -w
