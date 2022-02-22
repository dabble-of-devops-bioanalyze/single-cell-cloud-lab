FROM bitnami/airflow:2.2.3

ARG CELLXGENE_GATEWAY_VERSION=0.3.8
ENV CONDA_VERSION=4.10.3-7 \
    MAMBA_VERSION=0.17 \
    CONDA_ENV=cellxgene-gateway \
    NB_UID=1001 \
    SHELL=/bin/bash \
    LANG=C.UTF-8  \
    LC_ALL=C.UTF-8 \
    CONDA_DIR=/opt/bitnami/conda \
	DEBIAN_FRONTEND=noninteractive

ENV NB_PYTHON_PREFIX=${CONDA_DIR}/envs/${CONDA_ENV}
ENV PATH=${NB_PYTHON_PREFIX}/bin:${CONDA_DIR}/bin:${PATH}

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /tmp

USER root
RUN apt-get update -y; \
    apt-get install -y curl git wget unzip supervisor vim; \
    rm -rf /var/lib/apt/lists/*

# install aws cli
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
	unzip -q awscliv2.zip && \
	./aws/install && \
	rm -rf awscliv2.zip

USER 1001

RUN echo "Installing Miniforge..." \
    && URL="https://github.com/conda-forge/miniforge/releases/download/${CONDA_VERSION}/Miniforge3-${CONDA_VERSION}-Linux-x86_64.sh" \
    && wget --quiet ${URL} -O miniconda.sh \
    && /bin/bash miniconda.sh -u -b -p ${CONDA_DIR} \
    && rm miniconda.sh \
    && conda install -y -c conda-forge mamba=${MAMBA_VERSION} \
    && mamba clean -afy \
    && find ${CONDA_DIR} -follow -type f -name '*.a' -delete \
    && find ${CONDA_DIR} -follow -type f -name '*.pyc' -delete

COPY environment.yml /tmp
RUN mamba env create -f environment.yml && \
	mamba clean -yaf

# Cellxgene-gateway vars
ENV GATEWAY_PORT="5005"
ENV GATEWAY_ENABLE_ANNOTATIONS="True"
ENV CELLXGENE_LOCATION="${CONDA_DIR}/envs/cellxgene-gateway/bin/cellxgene"
ENV ANNOTATION_DIR="/opt/bitnami/airflow/data"
ENV HOME="/opt/bitnami"

RUN mkdir -p ${ANNOTATION_DIR}

# Airflow vars

ENV AIRFLOW_HOME="${HOME}/airflow"
ENV AIRFLOW__CORE__LOAD_EXAMPLES="False"
ENV AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION="False"

# Airflow
COPY airflow/dags /opt/bitnami/airflow/dags
RUN bash -c "source activate cellxgene-gateway && \
    mkdir -p ~/airflow/dags && \
    airflow db init && \
    airflow users create \
        --username admin \
        --firstname admin \
        --lastname admin \
        --password Password#123 \
        --role Admin \
        --email admin@admin.com"

# Copy in some dummy data for testing
# RUN mkdir -p /root/data/

ENV APP_DIR="/opt/bitnami/projects/app"
RUN mkdir -p ${APP_DIR}
COPY . ${APP_DIR}
WORKDIR ${APP_DIR}
ENV FLASK_APP=apps

# DEV
# If running in dev and don't want to use supervisord or s3 sync just run directly
# CMD ["python", "run.py"]

# PROD
# Run the supervisord that spins up the airflow-scheduler and the log
# CMD ["gunicorn",  "--config", "gunicorn-cfg.py", "run:app"]
CMD ["bash", "-c", "supervisord -c supervisord.conf; tail -f supervisord.log"]