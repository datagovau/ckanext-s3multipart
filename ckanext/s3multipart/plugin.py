import botocore
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
from pylons import config
import boto3
from botocore.client import Config
import ckan.model as model
from ckan.common import request, c

import ckan.lib.helpers as h
from logging import getLogger
import json

log = getLogger(__name__)
NO_CREDENTIALS_MESSAGE = "Amazon AWS credentials not set up for boto. "
"Please refer to https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration"
BAD_CREDENTIALS_MESSAGE = "Amazon AWS credentials not authorized. "
"Please refer to https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration"


def get_s3_role():
    return config.get('ckanext.s3multipart.s3_role', None)


def get_s3_bucket():
    return config.get('ckanext.s3multipart.s3_bucket', None)


def get_s3_region():
    return config.get('ckanext.s3multipart.s3_region', None)


def get_s3_prefix(dataset_name):
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj,
               'save': 'save' in request.params}
    dataset = toolkit.get_action('package_show')(context, {'id': dataset_name})
    prefix = config.get('ckanext.s3multipart.s3_prefix', '')
    org_prefix = True  # config.get('ckanext.s3multipart.s3_org_prefix', '')
    if prefix != '':
        prefix = prefix + "/"
    if org_prefix != '':
        prefix = prefix + dataset.get('owner_org', '') + "/"
    return prefix + dataset.get('id', '') + "/"


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
        return {'error': 'no dataset name/id specified'}
    if c.pkg_dict:
        pkg_dict = c.pkg_dict
    else:
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'save': 'save' in request.params}
        data_dict = {'id': dataset_name, 'include_tracking': False}
        pkg_dict = logic.get_action('package_show')(context, data_dict)
    if not pkg_dict or 'organization' not in pkg_dict \
            or pkg_dict['organization'].get('name', None) \
            not in config.get('ckanext.s3multipart.enabled_orgs', '').split():
        return {'error': 'organization not activated for s3 use'}
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
        assume_role_object['Credentials']['Expiration'] = str(assume_role_object['Credentials']['Expiration'])
        return assume_role_object

    except botocore.exceptions.NoCredentialsError:
        log.error(NO_CREDENTIALS_MESSAGE)
        h.flash_error(NO_CREDENTIALS_MESSAGE)
        return {'error': NO_CREDENTIALS_MESSAGE}
    except logic.NotAuthorized:
        log.error(BAD_CREDENTIALS_MESSAGE)
        h.flash_error(BAD_CREDENTIALS_MESSAGE)
        return {'error': BAD_CREDENTIALS_MESSAGE}


def get_presigned_post(dataset_name):
    if dataset_name == '':
        return {'error': 'no dataset name/id specified'}
    try:

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'save': 'save' in request.params}
        data_dict = {'id': dataset_name, 'include_tracking': False}
        pkg_dict = logic.get_action('package_show')(context, data_dict)
        if not pkg_dict or 'organization' not in pkg_dict \
                or pkg_dict['organization'].get('name', None) \
                not in config.get('ckanext.s3multipart.enabled_orgs', '').split():
            return {'error': 'organization not activated for s3 use'}

        logic.check_access('package_create', context)
        logic.check_access('package_update', context, {'id': dataset_name})

        s3 = boto3.client('s3', region_name=get_s3_region(), config=Config(signature_version='s3v4'))
        # Make sure everything posted is publicly readable
        fields = {"acl": "public-read"}

        # Ensure that the ACL isn't changed
        conditions = [
            {"acl": "public-read"},
            # ["content-length-range", 10, 100]
        ]

        # Generate the POST attributes
        post = s3.generate_presigned_post(Bucket=get_s3_bucket(), Key=get_s3_prefix(dataset_name) + "${filename}",
                                          Fields=fields, Conditions=conditions, ExpiresIn=3600)

        # demonstrate an example using curl command line tool
        #
        # make sure the file is at the end of the POST payload
        # else you get "Bucket POST must contain a field named 'key'.
        # If it is specified, please check the order of the fields."
        curl_example = 'curl -v '
        for k, v in post['fields'].items():
            curl_example += ' -F "%s=%s" ' % (k, v.replace('$', '\$'))
        curl_example += ' -F "file=@filename" %s' % post['url']
        post['curl_example'] = curl_example
        return post
    except logic.NotFound:
        return {'error': 'dataset not found'}
    except botocore.exceptions.NoCredentialsError:
        log.error(NO_CREDENTIALS_MESSAGE)
        h.flash_error(NO_CREDENTIALS_MESSAGE)
        return {'error': NO_CREDENTIALS_MESSAGE}
    except logic.NotAuthorized:
        log.error(BAD_CREDENTIALS_MESSAGE)
        h.flash_error(BAD_CREDENTIALS_MESSAGE)
        return {'error': BAD_CREDENTIALS_MESSAGE}


class S3MultipartPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes, inherit=True)

    def before_map(self, map):
        map.connect('/api/3/action/get_s3_auth/{dataset}',
                    controller='ckanext.s3multipart.controller:S3MultipartController', action='s3_auth')
        map.connect('/api/3/action/get_s3_post/{dataset}',
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
