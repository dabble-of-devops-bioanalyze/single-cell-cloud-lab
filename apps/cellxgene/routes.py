from turtle import update
from flask import render_template, request
from flask_login import login_required
from jinja2 import TemplateNotFound
import os

import datetime
import logging
from functools import wraps

from flask import (
    Flask,
    current_app,
    make_response,
    render_template,
    Blueprint,
    request,
    send_from_directory,
)
from flask_restful import Api, Resource
from flask import request


from apps.cellxgene import blueprint
from apps.logger import logger

from pprint import pprint
import server.common.rest as common_rest
from server.common.errors import DatasetAccessError, RequestException
from server.common.health import health_check
from server.common.utils.utils import StrictJSONEncoder

import os
from os.path import splitext, isdir

from server.common.annotations.local_file_csv import AnnotationsLocalFile
from server.common.config.base_config import BaseConfig
from server.common.errors import ConfigurationError, AnnotationsError
from server.data_common.matrix_loader import MatrixDataLoader

from server.common.config.app_config import AppConfig
from apps.cellxgene.config import set_default_config, update_datapath

DEFAULT_CONFIG = AppConfig()

ONE_WEEK = 7 * 24 * 60 * 60


ANNOTATION_DIR = os.environ.get("ANNOTATION_DIR", os.path.abspath("annotations"))
bucket = os.environ.get("CELLXGENE_BUCKET", "")


@blueprint.route("/")
def serve_cellxgene():
    logger.info("in serve_cellxgene")
    # datapath = request.args.get("datapath")
    # annotations_file = request.args.get("annotations", None)
    # logger.info(f"Datapath: {datapath}")
    try:
        # app_config = current_app.app_config
        # logger.info(app_config)

        # # datapath = "s3://cellxgene-gateway-example-set/pbmc3k.h5ad"
        # file_path = datapath
        # clean_file_path = file_path

        # if f"s3://{bucket}/" in clean_file_path:
        #     clean_file_path = clean_file_path.replace(f"s3://{bucket}/", "")
        # elif f"s3://{bucket}" in clean_file_path:
        #     clean_file_path = clean_file_path.replace(f"s3://{bucket}", "")

        # dataset_file = clean_file_path
        # if len(bucket):
        #     annotations_dir = os.path.join(
        #         ANNOTATION_DIR, bucket, f"{dataset_file}_annotations"
        #     )
        # else:
        #     annotations_dir = os.path.join(
        #         ANNOTATION_DIR, f"{dataset_file}_annotations"
        #     )

        # # user_generated_data_dir

        # set_default_config(app_config, datapath)
        # update_datapath(app_config, datapath)
        # current_app.data_adaptor = app_config.server_config.data_adaptor
        # dataset_config = app_config.get_dataset_config()

        # scripts = dataset_config.app__scripts
        # inline_scripts = dataset_config.app__inline_scripts
        # args = {"SCRIPTS": scripts, "INLINE_SCRIPTS": inline_scripts}
        from apps import sc_utils

        adata_found, adata_path, adaptor, dataset = sc_utils.load_adaptor()

    except Exception as e:
        logger.exception(e)

    return render_template(
        "cellxgene/index.html", segment="index"
    )


@blueprint.route("/dataset")
def dataset_index():
    app_config = current_app.app_config

    dataset_config = app_config.get_dataset_config()
    # scripts = dataset_config.app__scripts
    # inline_scripts = dataset_config.app__inline_scripts

    try:
        args = {}
        return render_template("cellxgene/index.html", **args)

    except DatasetAccessError as e:
        return common_rest.abort_and_log(
            e.status_code,
            f"Invalid dataset: {e.message}",
            loglevel=logging.INFO,
            include_exc_info=True,
        )


@blueprint.errorhandler(RequestException)
def handle_request_exception(error):
    return common_rest.abort_and_log(
        error.status_code, error.message, loglevel=logging.INFO, include_exc_info=True
    )
