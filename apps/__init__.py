import logging

from flask import Flask, url_for
from flask_appbuilder import AppBuilder, SQLA
from importlib import import_module
import os

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

#TODO This is a total hack
app.config['view_types'] = {}
app.config['url_mappings'] = {}

pathname_params = dict()
view_type = 'scanpy-embeddings'
title = "Scanpy Embedding Plots"
url_base = "/dash/scanpy/embeddings/"
if os.environ.get('SCRIPT_NAME', False):
    full_hosting_url = f"{os.environ.get('SCRIPT_NAME').rstrip('/')}{url_base}"
    pathname_params["routes_pathname_prefix"] =  url_base
    pathname_params["requests_pathname_prefix"] = full_hosting_url
    pathname_params['url_base_pathname'] = None
else:
    pathname_params['url_base_pathname'] = url_base
    pathname_params["routes_pathname_prefix"] = None
    pathname_params["requests_pathname_prefix"] = None
from apps.scanpy.embeddings.app import add_dash as add_dash_scanpy_embeddings
app = add_dash_scanpy_embeddings(app, appbuilder, title, **pathname_params)
app.config['url_mappings'][view_type] = url_base

pathname_params = dict()
view_type = 'scanpy-dataframes'
title = "Scanpy Data Frames"
url_base = "/dash/scanpy/dataframes/"
# if os.environ.get('SCRIPT_NAME', False):
#     url_base = f"{os.environ.get('SCRIPT_NAME').rstrip('/')}{url_base}"
from apps.scanpy.dataframes.app import add_dash as add_dash_scanpy_dataframes
app = add_dash_scanpy_dataframes(app, appbuilder, title, url_base)
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
