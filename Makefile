DOCKER_USERNAME="dabbleofdevops"
DOCKER_IMAGE="k8s-single-cell-cloud-lab"
SHELL := /bin/bash

# List of targets the `readme` target should call before generating the readme
export README_DEPS ?= docs/targets.md docs/terraform.md

-include $(shell curl -sSL -o .build-harness "https://git.io/build-harness"; echo .build-harness)

## Lint terraform code
lint:
	$(SELF) terraform/install terraform/get-modules terraform/get-plugins terraform/lint terraform/validate

build:
	docker build . -t dabbleofdevops/k8s-single-cell-cloud-lab:0.0.1
	docker build . -t dabbleofdevops/k8s-single-cell-cloud-lab:latest

push:
	$(MAKE) build
	docker push dabbleofdevops/k8s-single-cell-cloud-lab:0.0.1
	docker push dabbleofdevops/k8s-single-cell-cloud-lab:latest

dev:
	$(MAKE) compose/restart

compose/clean:
	docker-compose stop
	rm -rf airflow/logs/*
	rm -rf supervisord.log
	rm -rf supervisord.pid

compose/restart/build:
	$(MAKE) compose/clean
	docker-compose build
	docker-compose up -d
	docker-compose logs -f

compose/restart:
	$(MAKE) compose/clean
	docker-compose up -d
	docker-compose logs -f

compose/shell:
	docker-compose up -d
	docker-compose exec single-cell bash

compose/create-admin:
	docker-compose exec single-cell bash -c "flask fab create-admin"

download-readme:
	wget https://raw.githubusercontent.com/dabble-of-devops-bioanalyze/biohub-info/master/docs/README.md.gotmpl -O ./README.md.gotmpl

custom-init:
	docker run -it -v "$(shell pwd):/tmp/terraform-module" \
		-e README_TEMPLATE_FILE=/tmp/terraform-module/README.md.gotmpl \
		-w /tmp/terraform-module \
		cloudposse/build-harness:slim-latest init

custom-readme:
	$(MAKE) download-readme
	$(MAKE) custom-init
	docker run -it -v "$(shell pwd):/tmp/terraform-module" \
		-e README_TEMPLATE_FILE=/tmp/terraform-module/README.md.gotmpl \
		-w /tmp/terraform-module \
		cloudposse/build-harness:slim-latest readme
