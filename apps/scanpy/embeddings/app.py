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
from apps.dash.dash_func import apply_layout_with_auth, load_object, save_object
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

title = "Scanpy Embedding Plots"
basename = "scanpy"
url_base = "/dash/scanpy/embeddings/"

loc = dcc.Location(id="url", refresh=False)

header = html.H4(title, className="p-2 mb-2 text-center")
obs_dropdown = html.Div(
    [
        dbc.Label("Select 0 or more obs from your dataset."),
        dcc.Dropdown(
            id="obs_dropdown",
            options=[],
            multi=True,
        ),
    ],
    className="mb-4",
)
var_dropdown = html.Div(
    [
        dbc.Label("Select 0 or more vars from your dataset."),
        dcc.Dropdown(
            id="var_dropdown",
            options=[],
            multi=True,
        ),
    ],
    className="mb-4",
)
genes_dropdown = html.Div(
    [
        dbc.Label("Select 0 or more genes from your dataset."),
        dcc.Dropdown(
            id="genes_dropdown",
            options=[],
            multi=True,
        ),
    ],
    className="mb-4",
)
plot_type_dropdown = html.Div(
    [
        dbc.Label("Select a plot type."),
        dcc.Dropdown(
            id="plot_type_dropdown",
            options=[
                {"label": "umap", "value": "umap"},
                {"label": "pca", "value": "pca"},
                {"label": "tsne", "value": "tsne"},
            ],
            value="pca",
        ),
    ],
    className="mb-4",
)

controls = dbc.Card(
    [plot_type_dropdown, obs_dropdown, genes_dropdown],
    body=True,
)

# if we wanted to use matplotlib to return charts
# then just use an html image
img_holder = html.Div(
    [html.Img(id="plot_img", src="", className="img-fluid")],
    id="plot_div",
)

layout = dbc.Container(
    [
        loc,
        navbar,
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
                        "Once your dataset has loaded select one or more options. Scroll down to view your plots. You can optionally download any plot as a png by mousing over and selecting the camera icon.",
                        color="primary",
                    ),
                ]
            )
        ),
        html.Br(),
        dbc.Row([dbc.Col([controls], width=12)], id="controls"),
        html.Br(),
        # plots
        html.Div(
            [],
            id="scatter_plots",
        ),
    ],
    fluid=True,
    className="dbc",
)


d = os.path.dirname(__file__)
assets_folder = os.path.join(d, "assets")


def get_genes_as_df(dataset):
    # if loading with cellxgene there is a name_0 column
    if "name_0" in list(dataset.var.keys()):
        n_counts = list(dataset.var["name_0"])
        df = pd.DataFrame(n_counts, columns=["genes"])
    elif "n_counts" in list(dataset.var.keys()):
        n_counts = dataset.var["n_counts"]
        df = pd.DataFrame(n_counts, columns=["n_counts"])
        df["genes"] = df.index
    else:
        df = pd.DataFrame([], columns=["n_counts"])
        df["genes"] = df.index
    return df


# @lru_cache(maxsize=10, typed=False)
def build_options(vars, obs, genes):
    genes_options = []
    for gene in genes:
        genes_options.append({"label": gene, "value": gene})
    obs_options = []
    for ob in obs:
        if ob != "name_0":
            obs_options.append({"label": ob, "value": ob})
    vars_options = []
    for v in vars:
        vars_options.append({"label": v, "value": v})
    return vars_options, obs_options, genes_options


def scanpy_plot(dataset, plot_type, color):


    if plot_type == "pca":
        if "X_pca" not in list(dataset.obsm.keys()):
            sc.pp.pca(dataset)
        ax = sc_scatterplots.embedding(
            dataset, "pca", ncols=1, show=False, return_fig=False, color=color
        )
    elif plot_type == "umap":
        if "X_umap" not in list(dataset.obsm.keys()):
            sc.tl.umap(dataset)
        ax = sc_scatterplots.embedding(
            dataset, "umap", ncols=1, show=False, return_fig=False, color=color
        )
    elif plot_type == "tsne":
        if "X_tsne" not in list(dataset.obsm.keys()):
            sc.tl.tsne(dataset)
        ax = sc_scatterplots.embedding(
            dataset, "tsne", ncols=1, show=False, return_fig=False, color=color
        )

    if isinstance(ax, list):
        # ax[0].figure.set_size_inches(10, 5)
        # ax[0].figure.set_dpi(100)
        return fig_to_uri(ax[0].figure)
    else:
        # ax.figure.set_size_inches(10, 5)
        # ax.figure.set_dpi(100)
        return fig_to_uri(ax.figure)


def build_colors(var_values, obs_values, genes_values):
    color = []
    if var_values:
        color = color + var_values
    if obs_values:
        color = color + obs_values
    if genes_values:
        color = color + genes_values
    if len(color):
        return color
    else:
        return None


def dynamic_message(dataset_path=None, dataset_found=True):
    if dataset_found:
        return dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Alert(f"Loaded dataset: {dataset_path}", color="success"),
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
                            f"Unable to load dataset. Using {dataset_path}",
                            color="danger",
                        ),
                    ]
                )
            ]
        )


def dynamic_plot_maker(scatter_fig, histogram_fig=None, title="", index=0, error=False):
    if error:
        return dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Alert(
                            "Unable to render this plot: {error}", color="danger"
                        ),
                    ]
                )
            ]
        )
    elif histogram_fig:
        return dbc.Row(
            [
                dash.html.Hr(),
                html.H3(
                    title,
                ),
                dbc.Col(
                    [dcc.Graph(id=f"histogram-{index}", figure=histogram_fig)], width=12
                ),
                dbc.Col(
                    [dcc.Graph(id=f"scatter-{index}", figure=scatter_fig)], width=12
                ),
            ]
        )
    else:
        return dbc.Row(
            [dbc.Col([dcc.Graph(id=f"scatter-{index}", figure=scatter_fig)], width=12)]
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
        Output("obs_dropdown", "options"),
        Output("genes_dropdown", "options"),
        Output("scatter_plots", "children"),
        Output("message", "children"),
        Output("loading-output-message", "children"),
        Output("loading-output-spinner", "children"),
        # Output("loading-div", "children"),
        # Output(component_id="controls", component_property="hidden"),
        [
            Input("url", "pathname"),
            Input("plot_type_dropdown", "value"),
            Input("obs_dropdown", "value"),
            Input("genes_dropdown", "value"),
        ],
    )
    def update_graph(pathname, plot_type_value, obs_values, genes_values):
        # , plot_type, obs, var, genes
        var_values = []
        adata_path = None

        ## Load the dataset
        logger.info("Loading the dataset")
        adata_found = True

        try:
            adata_found, adata_path, adaptor, dataset = sc_utils.load_adaptor()
        except Exception as e:
            logger.exception(e)

        logger.info('Completed loading the dataset')
        logger.info(dataset)

        ## Generate dropdown options for obs and genes
        logger.info('Generating dropdown menus')
        color = build_colors(
            var_values=[], obs_values=obs_values, genes_values=genes_values
        )
        logger.info(color)

        df = get_genes_as_df(dataset)
        genes = list(df["genes"])
        obs = list(dataset.obs.keys())
        vars = list(dataset.var.keys())
        var_options, obs_options, genes_options = build_options(vars, obs, genes)

        # if we want to just matplotlib we can render it like this
        # out_url = scanpy_plot(dataset=dataset, plot_type=plot_type_value, color=color)

        ## Get the embedding plot data as a dataframe
        logger.info('Getting plot dataframe')
        sc_data_frame = scatterplot_utils.create_plot_dataframe(
            dataset, plot_type_value, color=color
        )
        if plot_type_value == "pca":
            labels = {
                "x": "PC1",
                "y": "PC2",
            }
        elif plot_type_value == "umap":
            labels = {
                "x": "UMAP1",
                "y": "UMAP2",
            }
        else:
            labels = {
                "x": "TSNE1",
                "y": "TSNE2",
            }
        dynamic_figs = []
        # Get the inputs and generate the corresponding plots
        if color:
            logger.info("Plotting with colors")
            for i, c in enumerate(color):
                # TODO Wrap this in try/catch block
                labels["color"] = color[i]
                title = f"{plot_type_value.upper()} {color[i]}"
                scatter_fig = px.scatter(
                    x=sc_data_frame["x"],
                    y=sc_data_frame["y"],
                    color=sc_data_frame[f"{color[i]}"],
                    labels=labels,
                    title=title,
                )

                histogram_fig = px.histogram(
                    sc_data_frame,
                    x=f"{color[i]}",
                    labels=labels,
                    title=title,
                )
                fig_0 = dynamic_plot_maker(
                    scatter_fig=scatter_fig,
                    histogram_fig=histogram_fig,
                    title=title,
                    index=i,
                )
                dynamic_figs.append(fig_0)
        else:
            logger.info("Plotting without colors")
            title = f"{plot_type_value.upper()}"
            scatter_fig = px.scatter(
                x=sc_data_frame["x"], y=sc_data_frame["y"], title=title, labels=labels
            )
            fig_0 = dynamic_plot_maker(
                scatter_fig=scatter_fig,
                histogram_fig=None,
                title=title,
                index=0,
            )
            dynamic_figs = [fig_0]

        message = dynamic_message(
            dataset_path=adata_path, dataset_found=adata_found
        )
        return [
            # Output("obs_dropdown", "options"),
            obs_options,
            # Output("genes_dropdown", "options"),
            genes_options,
            # Output("scatter_plots", "children"),
            dynamic_figs,
            # Output("message", "children"),
            message,
            # Output("loading-output-message", "children"),
            "",
            # Output("loading-output-spinner", "children"),
            "",
            # Output(component_id="controls", component_property="style"),
            # False,
        ]

    return app.server
