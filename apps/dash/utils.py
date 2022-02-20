import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
import typing
import dash_bootstrap_components as dbc
import dash
from dash import dash_table as dt
from dash import Dash, html, dcc
from flask import url_for, current_app


def fig_to_uri(in_fig, close_all=True, **save_args):
    """
    Save a figure as a URI
    :param in_fig:
    :return:
    """
    # type: (plt.Figure) -> str
    out_img = BytesIO()
    in_fig.savefig(out_img, format="png", **save_args)
    if close_all:
        in_fig.clf()
        plt.close("all")
    out_img.seek(0)  # rewind file
    encoded = base64.b64encode(out_img.read()).decode("ascii").replace("\n", "")
    return "data:image/png;base64,{}".format(encoded)


navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("DataSets", href='/datasets/list', target="_blank")),
        dbc.NavItem(dbc.NavLink("CellXGene", href='/cellxgene', target="_blank")),
        dbc.NavItem(dbc.NavLink("Embeddings", href='/dash/scanpy/embeddings', target="_blank")),
        dbc.NavItem(dbc.NavLink("DataFrames", href='/dash/scanpy/dataframes', target="_blank")),
        dbc.NavItem(
            dbc.NavLink(
                "Help", href="https://dabbleofdevopshelp.zendesk.com/", target="_blank"
            )
        ),
    ],
    brand="BioAnalyze - Single Cell Cloud Lab",
    brand_href="/datasets/list",
    color="primary",
    dark=True,
)


navbar_no_dataset = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("DataSets", href='/datasets/list', external_link=True, target="_blank")),
        dbc.NavItem(
            dbc.NavLink(
                "Help", external_link=True, href="https://dabbleofdevopshelp.zendesk.com/", target="_blank"
            )
        ),
    ],
    brand="BioAnalyze - Single Cell Cloud Lab",
    brand_href="/datasets/list",
    color="primary",
    dark=True,
)

loc = dcc.Location(id="url", refresh=False)
header = html.H4("No Dataset Loaded", className="p-2 mb-2 text-center")

layout_no_dataset = dbc.Container(
    [
        loc,
        navbar_no_dataset,
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
                                            "No dataset found. Please go to the datasets list page in order to choose a single cell dataset.",
                                            color="warning",
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
    ],
    fluid=True,
    className="dbc",
)
