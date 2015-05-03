import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
from pylons import config
import boto
import boto.sts
import ckan.model as model
from ckan.common import  request, c

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
        sts = boto.connect_sts(aws_access_key_id=config.get('ckanext.s3multipart.aws_key', None),
                               aws_secret_access_key=config.get('ckanext.s3multipart.aws_secret', None))
        tok = sts.get_session_token(duration = 3600)
        return tok.to_dict()
    except logic.NotAuthorized:
        return {}


class S3MultipartPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

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