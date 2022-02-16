# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from flask_login import current_user
from flask import redirect, current_app, session, has_app_context
from dash import dcc, html
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
    def serve_layout():
        app_config = current_app.config
        if not app_config['DATASET_LOADED']:
            return layout_no_dataset
        elif app_config['PUBLIC']:
            session_id = str(uuid.uuid4())
            clean_dir_store()
            return html.Div([html.Div(session_id, id="session_id", style={"display": "none"}), layout])
        elif current_user and current_user.is_authenticated:
            session_id = str(uuid.uuid4())
            clean_dir_store()
            return html.Div([html.Div(session_id, id="session_id", style={"display": "none"}), layout])
        loginurl = None
        if has_app_context():
            return dcc.Location(pathname=appbuilder.get_url_for_login, id="")
        return None

    app.config.suppress_callback_exceptions = True
    app.layout = serve_layout