SHELL := /bin/bash

DOCKERHUB_IMAGE="dabbleofdevops/k8s-single-cell-cloud-lab"
ECR_IMAGE="709825985650.dkr.ecr.us-east-1.amazonaws.com/dabble-of-devops/k8s-single-cell-cloud-lab"
P_ECR_IMAGE="018835827632.dkr.ecr.us-east-1.amazonaws.com/k8s-single-cell-cloud-lab"
VERSION?=0.0.1
SHA?=0.0.1
DT?="1"

# List of targets the `readme` target should call before generating the readme
export README_DEPS ?= docs/targets.md docs/terraform.md

-include $(shell curl -sSL -o .build-harness "https://git.io/build-harness"; echo .build-harness)

## Lint terraform code
lint:
	$(SELF) terraform/install terraform/get-modules terraform/get-plugins terraform/lint terraform/validate

build:
	docker build -t k8s-single-cell-cloud-lab:latest .

	docker tag k8s-single-cell-cloud-lab:latest $(ECR_IMAGE):$(VERSION)
	docker tag k8s-single-cell-cloud-lab:latest $(ECR_IMAGE):$(SHA)

	docker tag k8s-single-cell-cloud-lab:latest $(P_ECR_IMAGE):$(VERSION)
	docker tag k8s-single-cell-cloud-lab:latest $(P_ECR_IMAGE):$(SHA)

	docker tag k8s-single-cell-cloud-lab:latest $(DOCKERHUB_IMAGE):latest
	docker tag k8s-single-cell-cloud-lab:latest $(DOCKERHUB_IMAGE):$(VERSION)
	docker tag k8s-single-cell-cloud-lab:latest $(DOCKERHUB_IMAGE):$(SHA)

push:
	# $(MAKE) build
	# dockerhub push
	docker push $(DOCKERHUB_IMAGE):$(VERSION)
	docker push $(DOCKERHUB_IMAGE):$(SHA)
	docker push $(DOCKERHUB_IMAGE):latest

	# aws ecr push
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 709825985650.dkr.ecr.us-east-1.amazonaws.com
	docker push $(ECR_IMAGE):$(VERSION)
	docker push $(ECR_IMAGE):$(SHA)

	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 018835827632.dkr.ecr.us-east-1.amazonaws.com
	docker push $(P_ECR_IMAGE):$(VERSION)
	docker push $(P_ECR_IMAGE):$(SHA)

	echo "Pushed images"
	echo "$(DOCKERHUB_IMAGE):$(VERSION)"
	echo "$(DOCKERHUB_IMAGE):$(SHA)"
	echo "$(ECR_IMAGE):$(VERSION)"
	echo "$(ECR_IMAGE):$(SHA)"

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

# run as
# DT=$(date '+%Y-%m-%d_%H-%M-%S') make cve/test
# CVE-2021-3177
cve/test:
	docker build -t bitnami-airflow .
	docker tag bitnami-airflow \
		018835827632.dkr.ecr.us-east-1.amazonaws.com/bitnami-airflow:2.2.3-debian-10-r57-${DT}
	docker push 018835827632.dkr.ecr.us-east-1.amazonaws.com/bitnami-airflow:2.2.3-debian-10-r57-${DT}

