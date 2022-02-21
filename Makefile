SHELL := /bin/bash

DOCKERHUB_USERNAME="dabbleofdevops"
DOCKERHUB_IMAGE="k8s-single-cell-cloud-lab"
VERSION?=0.0.1
SHA?=0.0.1

# List of targets the `readme` target should call before generating the readme
export README_DEPS ?= docs/targets.md docs/terraform.md

-include $(shell curl -sSL -o .build-harness "https://git.io/build-harness"; echo .build-harness)

## Lint terraform code
lint:
	$(SELF) terraform/install terraform/get-modules terraform/get-plugins terraform/lint terraform/validate

build:
	docker build . -t dabbleofdevops/k8s-single-cell-cloud-lab:$(VERSION)
	docker build . -t dabbleofdevops/k8s-single-cell-cloud-lab:$(SHA)
	docker build . -t dabbleofdevops/k8s-single-cell-cloud-lab:latest
	docker build . -t 018835827632.dkr.ecr.us-east-1.amazonaws.com/k8s-single-cell-cloud-lab:latest
	docker build . -t 018835827632.dkr.ecr.us-east-1.amazonaws.com/k8s-single-cell-cloud-lab:$(VERSION)
	docker build . -t 018835827632.dkr.ecr.us-east-1.amazonaws.com/k8s-single-cell-cloud-lab:$(SHA)

push:
	$(MAKE) build
	# dockerhub push
	docker push dabbleofdevops/k8s-single-cell-cloud-lab:$(VERSION)
	docker push dabbleofdevops/k8s-single-cell-cloud-lab:$(SHA)
	docker push dabbleofdevops/k8s-single-cell-cloud-lab:latest

	# aws ecr push
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 018835827632.dkr.ecr.us-east-1.amazonaws.com
	docker push 018835827632.dkr.ecr.us-east-1.amazonaws.com/k8s-single-cell-cloud-lab:latest
	docker push 018835827632.dkr.ecr.us-east-1.amazonaws.com/k8s-single-cell-cloud-lab:$(VERSION)
	docker push 018835827632.dkr.ecr.us-east-1.amazonaws.com/k8s-single-cell-cloud-lab:$(SHA)

	echo "Pushed images"
	echo "dabbleofdevops/k8s-single-cell-cloud-lab:$(VERSION)"
	echo "dabbleofdevops/k8s-single-cell-cloud-lab:$(SHA)"
	echo "018835827632.dkr.ecr.us-east-1.amazonaws.com/k8s-single-cell-cloud-lab:$(VERSION)"
	echo "018835827632.dkr.ecr.us-east-1.amazonaws.com/k8s-single-cell-cloud-lab:$(SHA)"

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

compose:
	docker-compose up -d

compose/shell:
	docker-compose up -d
	docker-compose exec single-cell bash

compose/flask-routes:
	docker-compose up -d
	docker-compose exec single-cell bash -c "source activate cellxgene-gateway; flask routes"

compose/create-admin:
	docker-compose exec single-cell bash -c "flask fab create-admin"

# Terraform stuff

download-readme:
	wget https://raw.githubusercontent.com/dabble-of-devops-bioanalyze/biohub-info/master/docs/README.md.gotmpl -O ./README.md.gotmpl

custom-init:
	docker run -it -v "$(shell pwd):/tmp/terraform-module" \
		-e README_TEMPLATE_FILE=/tmp/terraform-module/README.md.gotmpl \
		-w /tmp/terraform-module \
		cloudposse/build-harness:slim-latest init

# generate the readme

custom-readme:
	$(MAKE) download-readme
	$(MAKE) custom-init
	docker run -it -v "$(shell pwd):/tmp/terraform-module" \
		-e README_TEMPLATE_FILE=/tmp/terraform-module/README.md.gotmpl \
		-w /tmp/terraform-module \
		cloudposse/build-harness:slim-latest readme

