import logging

from flask import Flask
from flask_appbuilder import AppBuilder, SQLA
from importlib import import_module

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
# Internal apps
#############################

from apps.scanpy.embeddings.app import add_dash as add_dash_scanpy_embeddings
app = add_dash_scanpy_embeddings(app, appbuilder)

from apps.scanpy.dataframes.app import add_dash as add_dash_scanpy_dataframes
app = add_dash_scanpy_dataframes(app, appbuilder)

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

"""
from sqlalchemy.engine import Engine
from sqlalchemy import event

#Only include this for SQLLite constraints
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # Will force sqllite contraint foreign keys
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
"""

from . import views
