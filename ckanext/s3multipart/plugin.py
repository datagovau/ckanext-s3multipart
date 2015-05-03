import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
from pylons import config
import boto
import boto.sts
import ckan.model as model
from ckan.common import  request, c

import ckan.lib.helpers as h
from logging import getLogger
log = getLogger(__name__)
def get_s3_bucket():
    return config.get('ckanext.s3multipart.s3_bucket', None)

def get_s3_region():
    return config.get('ckanext.s3multipart.s3_region', None)

def get_session_credentials():
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj,
               'save': 'save' in request.params}
    try:
        logic.check_access('package_create', context)
        sts = boto.connect_sts();
        tok = sts.get_session_token(duration=3600)
        return tok.to_dict()
    except boto.exception.NoAuthHandlerFound, e:
        log.error("Amazon AWS credentials not set up for boto. "
                  "Please refer to https://boto.readthedocs.org/en/latest/boto_config_tut.html")
        h.flash_error("Amazon AWS credentials not set up for boto. "
                      "Please refer to https://boto.readthedocs.org/en/latest/boto_config_tut.html")
        return {}
    except logic.NotAuthorized:
        return {}


class S3MultipartPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes, inherit=True)

    def before_map(self, map):
        map.connect('/api/s3_auth',
                    controller='ckanext.s3multipart.controller:S3MultipartController', action='s3_auth')
        return map
    ## ITemplateHelpers

    def get_helpers(self):
        return {
            'get_s3_bucket': get_s3_bucket,
            'get_s3_region': get_s3_region,
            'get_session_credentials': get_session_credentials
        }
    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 's3multipart')