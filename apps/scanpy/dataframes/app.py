# scanpy imports
import scanpy as sc
from scanpy.plotting._tools import scatterplots as sc_scatterplots

# dash imports
import dash
from dash import dash_table as dt
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import plotly.express as px
import fsspec
import matplotlib

# ds imports
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import base64
import itertools
import os
import pathlib
import urllib.parse
from io import BytesIO
import typing
import shutil

from functools import lru_cache

# app imports
from flask import url_for, session, current_app
from apps.dash.dash_func import apply_layout_with_auth, CustomDash, load_object, save_object
from apps.scanpy import scatterplot_utils
from apps.dash.utils import fig_to_uri, navbar
from apps import sc_utils, s3_utils
from apps.logger import logger

from server.data_anndata.anndata_adaptor import AnndataAdaptor

"""
AnnData object with n_obs × n_vars = 700 × 765
obs: 'bulk_labels', 'n_genes', 'percent_mito', 'n_counts', 'S_score', 'G2M_score', 'phase', 'louvain'
var: 'n_counts', 'means', 'dispersions', 'dispersions_norm', 'highly_variable'
uns: 'bulk_labels_colors', 'louvain', 'louvain_colors', 'neighbors', 'pca', 'rank_genes_groups'
obsm: 'X_pca', 'X_umap'
varm: 'PCs'
"""

title = "Scanpy Data Frames"
basename = "scanpy"

url_base = "/dash/scanpy/dataframes/"
if os.environ.get('SCRIPT_NAME', False):
    url_base = f"{os.environ.get('SCRIPT_NAME').rstrip('/')}{url_base}"

# loc = dcc.Location(id="url", refresh=False)

header = html.H4(title, className="p-2 mb-2 text-center")

dataframes = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H3("Variable Table"),
                        # dbc.Table.from_dataframe(var_df, striped=True, bordered=True, hover=True),
                        dt.DataTable(
                            id="var_df",
                            columns=[],
                            page_current=0,
                            page_size=20,
                            export_format="xlsx",
                            export_headers="display",
                            page_action="native",
                            sort_action='native',
                            filter_action='native',
                            row_deletable=False,
                            editable=False
                        ),
                    ]
                )
            ],
            id="var-table",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H3("Observations Table"),
                        dt.DataTable(
                            id="obs_df",
                            # columns=[{"name": i, "id": i} for i in obs_df.columns],
                            columns=[],
                            # page_current=0,
                            page_size=20,
                            export_format="xlsx",
                            export_headers="display",
                            page_action="native",
                            sort_action='native',
                            filter_action='native',
                            row_deletable=False,
                            editable=False
                        ),
                    ]
                )
            ],
            id="obs-table",
        ),
    ]
)


layout = dbc.Container(
    [
        header,
        html.Br(),
        # loading message
        html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div(
                                    [
                                        dbc.Alert(
                                            "Loading your dataset. Please be patient this can take several minutes. Do not refresh or navigate from this page. You will see a green success message when your dataset has loaded.",
                                            color="primary",
                                        ),
                                    ],
                                ),
                            ],
                            width=12,
                        ),
                    ],
                ),
            ],
            id="loading-output-message",
        ),
        # controls - select different options from the dataset to plot
        # loading spinner
        html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div(
                                    [
                                        dbc.Spinner(
                                            html.Div(id="loading-output-spinner"),
                                        ),
                                    ],
                                ),
                            ],
                            width=12,
                        ),
                    ],
                ),
            ],
        ),
        # controls - select different options from the dataset to plot
        html.Br(),
        # dataset status message
        html.Div([], id="message"),
        html.Br(),
        dbc.Row(
            dbc.Col(
                [
                    dbc.Alert(
                        "Once your dataset has loaded select one or more options. Scroll down to view your dataframes. You can optionally download any dataframe as an excel file by clicking the 'Export' button.",
                        color="primary",
                    ),
                ]
            )
        ),
        html.Br(),
        # plots
        dataframes,
    ],
    fluid=True,
    className="dbc",
)


d = os.path.dirname(__file__)
assets_folder = os.path.join(d, "assets")



def dynamic_message(adata_path=None, adata_found=True):
    if adata_found:
        return dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Alert(f"Loaded dataset: {adata_path}", color="success"),
                    ]
                )
            ]
        )
    else:
        return dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Alert(
                            f"Unable to load dataset. Using {adata_path}",
                            color="danger",
                        ),
                    ]
                )
            ]
        )


def add_dash(server, appbuilder):
    app = Dash(
        server=server,
        url_base_pathname=url_base,
        title=title,
        assets_folder=assets_folder,
        external_stylesheets=[dbc.themes.FLATLY],
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"},
            {"name": "author", "content": "BioAnalyze"},
        ],
    )
    apply_layout_with_auth(app, layout, appbuilder)

    @app.callback(
        Output("message", "children"),
        Output("loading-output-message", "children"),
        Output("loading-output-spinner", "children"),
        Output("var_df", "data"),
        Output("var_df", "columns"),
        Output("obs_df", "data"),
        Output("obs_df", "columns"),
        [
            Input("url", "pathname"),
        ],
    )
    def update_graph(
        url_path
    ):
        # , plot_type, obs, var, genes

        ## Load the dataset
        logger.info("Loading the dataset")
        adata_found, adata_path, adaptor, dataset = sc_utils.load_adaptor()
        logger.info(dataset)


        var_df = sc.get.var_df(dataset, keys=list(dataset.var.keys()))
        var_df_data = var_df.to_dict('records')
        logger.info(var_df.shape)
        obs_df = sc.get.obs_df(dataset, keys=list(dataset.obs.keys()))
        obs_df_data = obs_df.to_dict('records')
        message = dynamic_message(
            adata_path=adata_path, adata_found=adata_found
        )
        return [
            # Output("message", "children"),
            message,
            # Output("loading-output-message", "children"),
            "",
            # Output("loading-output-spinner", "children"),
            "",
            # Output("var_df", "data"),
            var_df_data,
            # Output("var_df", "columns"),
            [{"name": i, "id": i} for i in var_df.columns],
            # Output("obs_df", "data"),
            obs_df_data,
            # Output("obs_df", "columns"),
            [{"name": i, "id": i} for i in obs_df.columns],
        ]

    return app.server
