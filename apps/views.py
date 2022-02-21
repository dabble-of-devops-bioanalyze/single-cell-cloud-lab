from flask import render_template, current_app, request, redirect, url_for, session
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import ModelView, ModelRestApi
from flask_appbuilder.baseviews import BaseView
from flask_appbuilder import expose
from flask_appbuilder import has_access as admin_has_access
from apps.security import has_access
from apps.logger import logger
import s3fs
import os
import logging
from flask import flash
from flask_appbuilder import SimpleFormView
from flask_babel import lazy_gettext as _

# from apps.scanpy.app import add_dash as add_dash_scanpy
from apps.scanpy.embeddings import app as scanpy_embeding_app
from pprint import pprint

from . import appbuilder, db

def set_view_types():
    view_types = {
        "datasets": url_for('DatasetView.list'),
        "cellxgene": url_for("cellxgene.serve_cellxgene"),
        "scanpy-embeddings": url_for(current_app.config['url_mappings']['scanpy-embeddings']),
        "scanpy-dataframes": url_for(current_app.config['url_mappings']['scanpy-dataframes']),
    }
    pprint(view_types)
    current_app.config['view_types'] = view_types

class DatasetView(BaseView):
    route_base = "/datasets"

    @has_access
    @expose("/list/", methods=["GET", "POST"])
    def list(self):
        set_view_types()
        if request.method == "POST":
            current_app.config['DATASET_LOADED'] = True
            session["dataset"] = None
            session["csv"] = None
            view_type = request.form.get("view-type")
            dataset = request.form.get("dataset", None)
            csv = request.form.get("csv", None)
            if csv:
                csv = "s3://" + csv
                session["csv"] = csv
            if dataset:
                dataset = "s3://" + dataset
                session["adata_path"] = dataset
                return redirect(current_app.config['view_types'][view_type])

        if session.get('adata_path', False):
            current_app.config['DATASET'] = True
        else:
            current_app.config['DATASET'] = False

        s3 = s3fs.S3FileSystem()
        datasets = []
        h5ads = s3.glob(f"s3://{os.environ.get('CELLXGENE_BUCKET')}/**.h5ad")
        csvs = s3.glob(f"s3://{os.environ.get('CELLXGENE_BUCKET')}/**.csv")

        for h5ad in h5ads:
            datasets.append({"h5ad": h5ad})

        return self.render_template(
            "list.html",
            datasets=datasets,
            csvs=csvs,
            appbuilder=appbuilder,
            title="List Datasets",
        )


appbuilder.add_view_no_menu(DatasetView())
# appbuilder.add_link(
#     "List",
#     href="/datasets/list",
#     icon="fa-list",
#     category="Datasets",
#     category_icon="fa-list",
# )

"""
    Application wide 404 error handler
"""


@appbuilder.app.errorhandler(404)
def page_not_found(e):
    return (
        render_template(
            "404.html", base_template=appbuilder.base_template, appbuilder=appbuilder
        ),
        404,
    )


db.create_all()
