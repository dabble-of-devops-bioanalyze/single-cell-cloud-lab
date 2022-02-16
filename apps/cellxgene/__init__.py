import os
from flask import Blueprint
from flask import (
    Flask,
    current_app,
    make_response,
    render_template,
    Blueprint,
    request,
    send_from_directory,
)
import server
from server.common.config.app_config import AppConfig
from server.app.app import get_api_base_resources, get_api_dataroot_resources

import logging

path = os.path.dirname(server.__file__)
template_folder = os.path.join(path, "common", "web", "templates")

# /opt/bitnami/conda/envs/cellxgene-gateway/lib/python3.7/site-packages/server/common/web/templates/

DEFAULT_CONFIG = AppConfig()

api_version = "/api/v0.2"
api_path = "/cellxgene"


def register_additional_blueprints(app):
    if not os.path.exists(template_folder):
        logging.warn(f"template folder: {template_folder} does not exist")

    bp_base = Blueprint("bp_base", __name__, url_prefix=api_path)
    base_resources = get_api_base_resources(bp_base)
    app.register_blueprint(base_resources.blueprint)
    bp_api = Blueprint("api", __name__, url_prefix=f"{api_path}{api_version}")
    resources = get_api_dataroot_resources(bp_api)
    app.register_blueprint(resources.blueprint)


def add_url_rule(app):
    app.add_url_rule(
        "/cellxgene/static/<path:filename>",
        "static_assets",
        view_func=lambda filename: send_from_directory(
            os.path.join(path, "common/web/static"), filename
        ),
        methods=["GET"],
    )


# this is the webbp
# webbp = Blueprint("webapp", "server.common.web", template_folder="templates")
blueprint = Blueprint(
    "cellxgene",
    __name__,
    url_prefix="/cellxgene",
    template_folder=template_folder,
)
