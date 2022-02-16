import flask_appbuilder
import functools
import logging
from typing import TYPE_CHECKING
from flask_appbuilder._compat import as_unicode
from flask_appbuilder.const import (
    FLAMSG_ERR_SEC_ACCESS_DENIED,
    LOGMSG_ERR_SEC_ACCESS_DENIED,
    PERMISSION_PREFIX,
)
from flask_jwt_extended import verify_jwt_in_request
from flask_login import current_user

from flask import (
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    request,
    Response,
    url_for,
)

from apps import app
log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from flask_appbuilder.api import BaseApi

def has_access(f):
    """
    Use this decorator to enable public access to your site. If the app.config['PUBLIC'] == True, then Public access is enabled.
    """
    access_enabled = True
    with app.app_context():
        if not current_app.config.get('PUBLIC', False):
            log.info('Public access not enabled')
            access_enabled = False
        else:
            log.info('Public access is enabled')

    if hasattr(f, "_permission_name"):
        permission_str = f._permission_name
    else:
        permission_str = f.__name__

    def wraps(self, *args, **kwargs):
        if access_enabled:
            return f(self, *args, **kwargs)
        else:
            permission_str = f"{PERMISSION_PREFIX}{f._permission_name}"
            if self.method_permission_name:
                _permission_name = self.method_permission_name.get(f.__name__)
                if _permission_name:
                    permission_str = f"{PERMISSION_PREFIX}{_permission_name}"
            if permission_str in self.base_permissions and self.appbuilder.sm.has_access(
                permission_str, self.class_permission_name
            ):
                return f(self, *args, **kwargs)
            else:
                log.warning(
                    LOGMSG_ERR_SEC_ACCESS_DENIED.format(
                        permission_str, self.__class__.__name__
                    )
                )
                flash(as_unicode(FLAMSG_ERR_SEC_ACCESS_DENIED), "danger")
            return redirect(
                url_for(
                    self.appbuilder.sm.auth_view.__class__.__name__ + ".login",
                    next=request.url,
                )
            )

    f._permission_name = permission_str
    return functools.update_wrapper(wraps, f)