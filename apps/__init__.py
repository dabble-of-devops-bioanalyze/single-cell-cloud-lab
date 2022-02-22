from distutils.command.build import build
import logging

from flask import Flask, url_for
from flask_appbuilder import AppBuilder, SQLA
from importlib import import_module
from dash import Dash, html, dcc
import os
import dash_bootstrap_components as dbc

# cellxgene
from server.common.config.app_config import AppConfig

# Internal apps


"""
 Logging configuration
"""

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
logging.getLogger().setLevel(logging.INFO)

from .indexview import MyIndexView

app = Flask(__name__)
app.config.from_object("config")
db = SQLA(app)
appbuilder = AppBuilder(app, db.session, indexview=MyIndexView)

#############################
# Dash apps
#############################

def build_pathname_params(url_base):
    pathname_params = dict()
    pathname_params['url_base_pathname'] = None
    pathname_params["routes_pathname_prefix"] = None
    pathname_params["requests_pathname_prefix"] = None
    if os.environ.get('SCRIPT_NAME', False):
        # if running under a proxy such as nginx or shinyproxy, you need to add the fullpathname to the requests
        full_hosting_url = f"{os.environ.get('SCRIPT_NAME').rstrip('/')}{url_base}"
        pathname_params["routes_pathname_prefix"] =  url_base
        pathname_params["requests_pathname_prefix"] = full_hosting_url
    else:
        pathname_params['url_base_pathname'] = url_base
    return pathname_params

#TODO This is a total hack
app.config['view_types'] = {}
app.config['url_mappings'] = {}

view_type = 'scanpy-embeddings'
title = "Scanpy Embedding Plots"
url_base = "/dash/scanpy/embeddings/"
pathname_params = build_pathname_params(url_base)
from apps.scanpy.embeddings.app import add_dash as add_dash_scanpy_embeddings
app = add_dash_scanpy_embeddings(app, appbuilder, title, **pathname_params)
app.config['url_mappings'][view_type] = url_base

view_type = 'scanpy-dataframes'
title = "Scanpy Data Frames"
url_base = "/dash/scanpy/dataframes/"
pathname_params = build_pathname_params(url_base)
from apps.scanpy.dataframes.app import add_dash as add_dash_scanpy_dataframes
app = add_dash_scanpy_dataframes(app, appbuilder, title, **pathname_params)
app.config['url_mappings'][view_type] = url_base

#############################
# CellxGene
#############################

# cellxgene config
app_config = AppConfig()
app.app_config = app_config
server_config = app_config.server_config
app.data_adaptor = server_config.data_adaptor

# add cellxgene blueprints
module_name = "cellxgene"
module = import_module("apps.{}.routes".format(module_name))
app.register_blueprint(module.blueprint)
from apps.cellxgene import add_url_rule, register_additional_blueprints

register_additional_blueprints(app)
add_url_rule(app)

from . import views
