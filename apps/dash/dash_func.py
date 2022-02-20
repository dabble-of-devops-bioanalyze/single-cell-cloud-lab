# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from flask_login import current_user
from flask import redirect, current_app, session, has_app_context, url_for
from dash import dcc, html
import dash_bootstrap_components as dbc
import pandas as pd
import uuid
import os
import pickle
from apps.dash.utils import layout_no_dataset


def save_object(obj, session_id, name):
    os.makedirs("dir_store", exist_ok=True)
    file = "dir_store/{}_{}".format(session_id, name)
    pickle.dump(obj, open(file, "wb"))


def load_object(session_id, name):
    file = "dir_store/{}_{}".format(session_id, name)
    obj = pickle.load(open(file, "rb"))
    os.remove(file)
    return obj


def clean_dir_store():
    if os.path.isdir("dir_store"):
        file_list = pd.Series("dir_store/" + i for i in os.listdir("dir_store"))
        mt = file_list.apply(lambda x: datetime.fromtimestamp(os.path.getmtime(x))).astype(str)
        for i in file_list[mt < str(datetime.now() - timedelta(hours=3))]:
            os.remove(i)


def apply_layout_with_auth(app, layout, appbuilder):
    def build_navbar():
        return dbc.NavbarSimple(
        children=[
            dcc.Location(id='url', refresh=False),
            dbc.NavItem(dbc.NavLink("DataSets", href=current_app.config['view_types']['datasets'], external_link=True, target="_blank")),
            dbc.NavItem(dbc.NavLink("CellXGene", href=url_for('cellxgene.serve_cellxgene'), external_link=True, target="_blank")),
            dbc.NavItem(dbc.NavLink("Embeddings", href=url_for('/dash/scanpy/embeddings/'),external_link=True, target="_blank")),
            dbc.NavItem(dbc.NavLink("DataFrames", href=url_for('/dash/scanpy/dataframes/'),external_link=True, target="_blank")),
            dbc.NavItem(
                dbc.NavLink(
                    "Help", href="https://dabbleofdevopshelp.zendesk.com/", target="_blank", external_link=True
                )
            ),
        ],
        brand="BioAnalyze - Single Cell Cloud Lab",
        brand_href=url_for('DatasetView.list'),
        color="primary",
        dark=True,
    )
    def serve_layout():
        app_config = current_app.config
        if not app_config['DATASET_LOADED']:
            return layout_no_dataset
        elif app_config['PUBLIC']:
            session_id = str(uuid.uuid4())
            clean_dir_store()
            return html.Div([html.Div(session_id, id="session_id", style={"display": "none"}),dcc.Location(id='url', refresh=False), dbc.Container([build_navbar(),     ], fluid=True,className="dbc",), layout])
        elif current_user and current_user.is_authenticated:
            session_id = str(uuid.uuid4())
            clean_dir_store()
            return html.Div([html.Div(session_id, id="session_id", style={"display": "none"}),dcc.Location(id='url', refresh=False), dbc.Container([build_navbar(),     ], fluid=True,className="dbc",), layout])
        loginurl = None
        if has_app_context():
            return dcc.Location(pathname=appbuilder.get_url_for_login, id="")
        return None

    app.config.suppress_callback_exceptions = True
    app.layout = serve_layout