import botocore
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
from pylons import config
import boto3
import ckan.model as model
from ckan.common import request, c

import ckan.lib.helpers as h
from logging import getLogger
import json

log = getLogger(__name__)


def get_s3_role():
    return config.get('ckanext.s3multipart.s3_role', None)


def get_s3_bucket():
    return config.get('ckanext.s3multipart.s3_bucket', None)


def get_s3_region():
    return config.get('ckanext.s3multipart.s3_region', None)


def get_s3_prefix(dataset_name):
    dataset = toolkit.get_action('package_show')({'model': model},
                                                 {'id': dataset_name})
    prefix = config.get('ckanext.s3multipart.s3_prefix', '')
    org_prefix = True  # config.get('ckanext.s3multipart.s3_org_prefix', '')
    if prefix != '':
        prefix = prefix + "/"
    if org_prefix != '':
        prefix = prefix + dataset['owner_org'] + "/"
    return prefix + dataset['id'] + "/"


def _get_policy(dataset_name):
    # http://blogs.aws.amazon.com//security/post/Tx1P2T3LFXXCNB5/Writing-IAM-policies-Grant-access-to-user-specific-folders-in-an-Amazon-span-cla
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowUserFolderOperations",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject*",
                    "s3:GetBucketLocation",
                    "s3:PutObject*",
                    "s3:DeleteObject",
                    "s3:*Multipart*"
                ],
                "Resource": "arn:aws:s3:::" + get_s3_bucket() + "/" + get_s3_prefix(dataset_name) + "*"
            },

            {
                "Sid": "AllowListingOfUserFolder",
                "Action": ["s3:ListBucket"],
                "Effect": "Allow",
                "Resource": "arn:aws:s3:::" + get_s3_bucket(),
                "Condition": {"StringLike": {"s3:prefix": [get_s3_prefix(dataset_name)]}}
            },
            {
                "Sid": "FindMyBucket",
                "Effect": "Allow",
                "Action": "s3:ListAllMyBuckets",
                "Resource": "arn:aws:s3:::*",
                "Condition": {"StringLike": {"s3:prefix": [get_s3_bucket()]}}
            },
            {
                "Sid": "AllowRootListingWithoutPrefix",
                "Action": [
                    "s3:ListBucket"
                ],
                "Effect": "Allow",
                "Resource": [
                    "arn:aws:s3:::" + get_s3_bucket()
                ],
                "Condition": {
                    "Null": {
                        "s3:prefix": "true"
                    },
                    "StringEquals": {
                        "s3:delimiter": [
                            "/"
                        ]
                    }
                }
            }
        ]
    })


def get_session_credentials(dataset_name):
    if dataset_name == '':
        return {}
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj,
               'save': 'save' in request.params}
    try:
        logic.check_access('package_create', context)
        logic.check_access('package_update', context, {'id': dataset_name})

        sess = boto3.Session()
        sts_connection = sess.client('sts')
        assume_role_object = sts_connection.assume_role(RoleArn=get_s3_role(),
                                                        RoleSessionName=(c.user + "@" + config.get('ckan.site_id', ''))[
                                                                        :32], DurationSeconds=3600,
                                                        Policy=_get_policy(dataset_name))
        return assume_role_object['Credentials']

    except botocore.exceptions.NoCredentialsError:
        log.error("Amazon AWS credentials not set up for boto. "
                  "Please refer to https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration")
        h.flash_error("Amazon AWS credentials not set up for boto. "
                      "Please refer to https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration")
        return {}
    except logic.NotAuthorized:
        log.error("Amazon AWS credentials not authorized. "
                  "Please refer to https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration")
        h.flash_error("Amazon AWS credentials not authorized. "
                      "Please refer to https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration")
        return {}


def get_presigned_post(dataset_name):
    if dataset_name == '':
        return {}
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'save': 'save' in request.params}
    try:
        logic.check_access('package_create', context)
        logic.check_access('package_update', context, {'id': dataset_name})

        s3Client = boto3.client('s3')
        s3Client.generate_presigned_url('get_object', Params={'Bucket': get_s3_bucket(), 'Key': 'hello.txt'},
                                        ExpiresIn=100)

    except boto.exception.NoAuthHandlerFound, e:
        log.error("Amazon AWS credentials not set up for boto. "
                  "Please refer to https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration")
        h.flash_error("Amazon AWS credentials not set up for boto. "
                      "Please refer to https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration")
        return {}
    except logic.NotAuthorized:
        log.error("Amazon AWS credentials not authorized. "
                  "Please refer to https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration")
        h.flash_error("Amazon AWS credentials not authorized. "
                      "Please refer to https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration")
        return {}


class S3MultipartPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes, inherit=True)

    def before_map(self, map):
        map.connect('/api/s3_auth',
                    controller='ckanext.s3multipart.controller:S3MultipartController', action='s3_auth')
        map.connect('/api/s3_post',
                    controller='ckanext.s3multipart.controller:S3MultipartController', action='s3_post')
        return map

    ## ITemplateHelpers

    def get_helpers(self):
        return {
            'get_s3_bucket': get_s3_bucket,
            'get_s3_region': get_s3_region,
            'get_s3_prefix': get_s3_prefix,
            'get_session_credentials': get_session_credentials
        }

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 's3multipart')
