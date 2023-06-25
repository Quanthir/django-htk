# Python Standard Library Imports
from functools import wraps

# Third Party (PyPI) Imports
import rollbar

# Django Imports
from django.http import (
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
)

# HTK Imports
from htk.api.utils import (
    json_response_forbidden,
    json_response_not_found,
)
from htk.decorators.session_keys import DEPRECATED_ROLLBAR_NOTIFIED
from htk.utils.request import get_current_request


def deprecated(func):
    """Decorator for reporting deprecated function calls

    Use this decorator sparingly, because we'll be charged if we make too many Rollbar notifications
    """
    @wraps(func)
    def wrapped(*args, **kwargs):
        # try to get a request, may not always succeed
        request = get_current_request()
        # notify a maximum of once per function per request/session
        if request:
            if DEPRECATED_ROLLBAR_NOTIFIED not in request.session:
                deprecated_notifications = {}
                request.session[DEPRECATED_ROLLBAR_NOTIFIED] = deprecated_notifications
            deprecated_notifications = request.session[DEPRECATED_ROLLBAR_NOTIFIED]
            key = '%s' % func
            # first get it
            already_notified = deprecated_notifications.get(key, False)
            # then mark it
            deprecated_notifications[key] = True
        else:
            already_notified = False

        if not already_notified:
            rollbar.report_message('Deprecated function call warning: %s' % func, 'warning', request)
        return func(*args, **kwargs)
    return wrapped


class restful_obj_seo_redirect(object):
    """Decorator for redirecting a RESTful object view to its SEO canonical URL
    if not already using it
    """
    def __init__(self, cls, obj_id_key):
        self.cls = cls
        self.obj_id_key = obj_id_key

    def __call__(self, view_fn):
        @wraps(view_fn)
        def wrapped(*args, **kwargs):
            obj_id = kwargs.get(self.obj_id_key)
            obj = get_object_or_404(self.cls, id=obj_id)
            seo_title = kwargs.get('seo_title')

            if not obj.has_seo_title_match(seo_title):
                # prevent tampering of URLs
                # redirect to the canonical URL for this object
                response = redirect(obj.get_absolute_url(), permanent=True)
            else:
                # store the retrieved object to avoid re-fetching
                retrieved_key = self.cls.__name__.lower()
                kwargs[retrieved_key] = obj
                response = view_fn(*args, **kwargs)
            return response
        return wrapped


class content_type_based(object):
    """Abstract Content Type Based Decorator
    
    Helps to create decorators based on content type to response.
    """
    def __init__(self, content_type='text/html'):
        self.content_type = content_type

    @property
    def is_ajax_request(self):
        value = self.content_type == 'application/json'
        return value

    @property
    def response_not_found(self):
        response = (
            json_response_not_found()
            if self.is_ajax_request
            else HttpResponseNotFound()
        )
        return response

    @property
    def response_forbidden(self):
        response = (
            json_response_forbidden()
            if self.is_ajax_request
            else HttpResponseForbidden()
        )
        return response


def disable_for_loaddata(signal_handler):
    """Decorator that turns off signal handlers when loading fixture data.

    See:
    - https://stackoverflow.com/a/15625121/865091
    - https://code.djangoproject.com/ticket/17880
    - https://stackoverflow.com/questions/3499791/how-do-i-prevent-fixtures-from-conflicting-with-django-post-save-signal-code
    - https://docs.djangoproject.com/en/dev/ref/signals/#post-save
    """
    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if kwargs.get('raw'):
            return
        signal_handler(*args, **kwargs)
    return wrapper
