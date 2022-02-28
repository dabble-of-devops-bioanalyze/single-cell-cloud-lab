from flask import render_template, request, redirect, url_for, session, current_app
from server.default_config import default_config
from server.app.app import Server
from server.common.config.app_config import AppConfig
from server.common.errors import DatasetAccessError, ConfigurationError
from server.common.utils.utils import sort_options
from server.common.annotations.local_file_csv import AnnotationsLocalFile
from server.common.config.base_config import BaseConfig
from server.common.errors import ConfigurationError, AnnotationsError
from server.data_common.matrix_loader import MatrixDataLoader
from server.common.errors import DatasetAccessError, RequestException
import server.common.rest as common_rest

import os
from functools import lru_cache
import logging
from apps.logger import logger
from apps import s3_utils

DEFAULT_CONFIG = AppConfig()

ANNOTATION_DIR = os.environ.get("ANNOTATION_DIR", os.path.abspath("annotations"))
CELLXGENE_BUCKET = os.environ.get("CELLXGENE_BUCKET", False) or os.environ.get('BUCKET')
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')

# these all come from the click cli options
# https://github.com/chanzuckerberg/cellxgene/blob/3ebbb0ccbf91955fa27913ac73d73298e018311c/server/cli/launch.py
def set_default_config(
    app_config,
    datapath,
    verbose=DEFAULT_CONFIG.server_config.app__verbose,
    debug=DEFAULT_CONFIG.server_config.app__debug,
    open_browser=DEFAULT_CONFIG.server_config.app__open_browser,
    port=5005,
    host="0.0.0.0",
    embedding=DEFAULT_CONFIG.dataset_config.embeddings__names,
    obs_names=DEFAULT_CONFIG.server_config.single_dataset__obs_names,
    var_names=DEFAULT_CONFIG.server_config.single_dataset__var_names,
    max_category_items=DEFAULT_CONFIG.dataset_config.presentation__max_categories,
    disable_custom_colors=False,
    diffexp_lfc_cutoff=DEFAULT_CONFIG.dataset_config.diffexp__lfc_cutoff,
    title=DEFAULT_CONFIG.server_config.single_dataset__title,
    scripts=DEFAULT_CONFIG.dataset_config.app__scripts,
    about=DEFAULT_CONFIG.server_config.single_dataset__about,
    disable_annotations=not DEFAULT_CONFIG.dataset_config.user_annotations__enable,
    annotations_file=DEFAULT_CONFIG.dataset_config.user_annotations__local_file_csv__file,
    user_generated_data_dir=DEFAULT_CONFIG.dataset_config.user_annotations__local_file_csv__directory,
    gene_sets_file=DEFAULT_CONFIG.dataset_config.user_annotations__local_file_csv__gene_sets_file,
    disable_gene_sets_save=DEFAULT_CONFIG.dataset_config.user_annotations__gene_sets__readonly,
    backed=DEFAULT_CONFIG.server_config.adaptor__anndata_adaptor__backed,
    disable_diffexp=not DEFAULT_CONFIG.dataset_config.diffexp__enable,
    dump_default_config=False,
    x_approximate_distribution=DEFAULT_CONFIG.dataset_config.X_approximate_distribution,
):

    cli_config = AppConfig()
    server_config = app_config.server_config

    cli_config.update_server_config(
        # app__verbose=verbose,
        # app__debug=debug,
        # app__host=host,
        # app__port=port,
        # app__open_browser=open_browser,
        single_dataset__datapath=datapath,
        single_dataset__title=title,
        single_dataset__about=about,
        single_dataset__obs_names=obs_names,
        single_dataset__var_names=var_names,
        adaptor__anndata_adaptor__backed=backed,
    )
    cli_config.update_dataset_config(
        app__scripts=scripts,
        user_annotations__enable=not disable_annotations,
        user_annotations__local_file_csv__file=annotations_file,
        user_annotations__local_file_csv__directory=user_generated_data_dir,
        user_annotations__local_file_csv__gene_sets_file=gene_sets_file,
        user_annotations__gene_sets__readonly=disable_gene_sets_save,
        presentation__max_categories=max_category_items,
        presentation__custom_colors=not disable_custom_colors,
        embeddings__names=embedding,
        diffexp__enable=not disable_diffexp,
        diffexp__lfc_cutoff=diffexp_lfc_cutoff,
        X_approximate_distribution=x_approximate_distribution,
    )

    diff = cli_config.server_config.changes_from_default()
    changes = {key: val for key, val, _ in diff}
    app_config.update_server_config(**changes)

    diff = cli_config.dataset_config.changes_from_default()
    changes = {key: val for key, val, _ in diff}
    app_config.update_dataset_config(**changes)

    if not server_config.app__flask_secret_key:
        app_config.update_server_config(app__flask_secret_key="SparkleAndShine")
    return


@lru_cache(maxsize=10, typed=False)
def load_matrix(app_config, datapath):
    matrix_data_loader = MatrixDataLoader(datapath, app_config=app_config)
    return matrix_data_loader.open(app_config)

def load_matrix_no_cache():
    app_config = current_app.app_config
    datapath = app_config.server_config.single_dataset__datapath
    matrix_data_loader = MatrixDataLoader(datapath, app_config=app_config)
    return matrix_data_loader.open(app_config)

def generate_annotation_dir(anndata_path):
    file_path = anndata_path
    clean_file_path = file_path

    if f"s3://{CELLXGENE_BUCKET}/" in clean_file_path:
        clean_file_path = clean_file_path.replace(f"s3://{CELLXGENE_BUCKET}/", "")
    elif f"s3://{CELLXGENE_BUCKET}" in clean_file_path:
        clean_file_path = clean_file_path.replace(f"s3://{CELLXGENE_BUCKET}", "")

    dataset_file = clean_file_path
    if len(CELLXGENE_BUCKET):
        annotations_dir = os.path.join(
            ANNOTATION_DIR, CELLXGENE_BUCKET, f"{dataset_file}_annotations"
        )
    else:
        annotations_dir = os.path.join(ANNOTATION_DIR, f"{dataset_file}_annotations")

    logger.info(f"Annotations dir: {annotations_dir}")
    os.makedirs(annotations_dir, exist_ok=True)
    return annotations_dir


@lru_cache(maxsize=10, typed=False)
def update_datapath(adata_path, csv_path):
    try:
        app_config = current_app.app_config
        logger.info(app_config)
        set_default_config(app_config, adata_path)

        app_config.update_server_config(
            single_dataset__datapath=adata_path,
        )
        server_config = app_config.server_config
        app_config.dataset_config.user_annotations__local_file_csv__directory = DEFAULT_CONFIG.dataset_config.user_annotations__local_file_csv__directory
        app_config.dataset_config.user_annotations__local_file_csv__file =  DEFAULT_CONFIG.dataset_config.user_annotations__local_file_csv__file

        if csv_path:
            logger.info(f'Got a csv: {csv_path}')
            out, t_dataset = s3_utils.sync_dataset_down(csv_path)
            logger.info('Downloaded csv to local storage')
            logger.info(t_dataset)
            app_config.dataset_config.user_annotations__local_file_csv__file = out
        else:
            annotation_dir = generate_annotation_dir(adata_path)
            app_config.dataset_config.user_annotations__local_file_csv__directory = annotation_dir

        app_config.server_config.data_locator__s3__region_name = AWS_REGION
        server_config.data_adaptor = load_matrix(app_config, adata_path)
        current_app.data_adaptor = app_config.server_config.data_adaptor

        def messagefn(message):
            print("[cellxgene] " + message)

        # This MUST be here or the app does not work!
        app_config.complete_config(messagefn)
    except DatasetAccessError as e:
        return common_rest.abort_and_log(
            e.status_code,
            f"Invalid dataset: {e.message}",
            loglevel=logging.INFO,
            include_exc_info=True,
        )
