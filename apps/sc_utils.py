from flask import current_app, session

import scanpy as sc
from server.common.annotations.local_file_csv import AnnotationsLocalFile
from server.common.config import DEFAULT_SERVER_PORT
from server.common.config.app_config import AppConfig
from server.common.fbs.matrix import encode_matrix_fbs
from server.common.utils.data_locator import DataLocator
from server.common.utils.utils import find_available_port
from server.data_common.matrix_loader import MatrixDataType, MatrixDataLoader

from server.common.compute import diffexp_generic
from server.data_common.matrix_loader import MatrixDataLoader
from apps.cellxgene.config import (
    set_default_config,
    update_datapath,
    load_matrix_no_cache,
)

from functools import lru_cache
import pandas as pd
import numpy as np
import os

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
import logging
from apps.logger import logger

DEFAULT_CONFIG = AppConfig()

ONE_WEEK = 7 * 24 * 60 * 60
ANNOTATION_DIR = os.environ.get("ANNOTATION_DIR", os.path.abspath("annotations"))
bucket = os.environ.get("CELLXGENE_BUCKET", "")

"""
Cellxgene has many handy loading functions

But they are all loaded into the flask app config

So we're stealing some code from the tests
"""


# do not cache this function!
def load_adaptor():
    logger.info("loading adaptor")
    adata_found = True
    csv_path = None
    if session.get("csv"):
        csv_path = session.get("csv")
    if session.get("adata_path"):
        logger.info("Session data found.")
        adata_path = session.get("adata_path")
        update_datapath(adata_path, csv_path)
        logger.info("Loading matrix")
        adaptor = load_matrix(adata_path)
        logger.info('Completed loading matrix')
        logger.info(adaptor)
        dataset = adaptor.data
        app_config = current_app.app_config
        current_app.data_adaptor = adaptor
        app_config.server_config.data_adaptor = adaptor
    else:
        logger.info('Session data not found')
        adata_found = False
        adaptor = None
        adata_path = "scanpy pbmc68k_reduced"
        dataset = sc.datasets.pbmc68k_reduced()
    return adata_found, adata_path, adaptor, dataset


@lru_cache(maxsize=10, typed=False)
def load_matrix(adata_path):
    logger.info(f'Loading matrix {adata_path}')
    app_config = current_app.app_config
    matrix_data_loader = MatrixDataLoader(adata_path, app_config=app_config)
    data_adaptor = matrix_data_loader.open(app_config)
    return data_adaptor


def get_genes_as_df(adata):
    # if loading with cellxgene there is a name_0 column
    if "name_0" in list(adata.var.keys()):
        n_counts = list(adata.var["name_0"])
        df = pd.DataFrame(n_counts, columns=["genes"])
    elif "n_counts" in list(adata.var.keys()):
        n_counts = adata.var["n_counts"]
        df = pd.DataFrame(n_counts, columns=["n_counts"])
        df["genes"] = df.index
    else:
        df = pd.DataFrame([], columns=["n_counts"])
        df["genes"] = df.index
    return df


def check_for_plot_type(adata, plot_type):
    logger.info("In check_for_plot_type")
    logger.info(f"Plot type: {plot_type}")

    if plot_type == "pca" and "X_pca" not in list(adata.obsm.keys()):
        logger.info("Running PCA")
        sc.pp.pca(adata)
        load_matrix_no_cache()
    elif plot_type == "umap" and "X_umap" not in list(adata.obsm.keys()):
        logger.info("Running UMAP")
        sc.tl.umap(adata)
        load_matrix_no_cache()
    elif plot_type == "tsne" and "X_tsne" not in list(adata.obsm.keys()):
        logger.info("Running tsne")
        sc.tl.tsne(adata)
        load_matrix_no_cache()
    else:
        return
