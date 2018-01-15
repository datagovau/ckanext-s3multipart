from ckan.lib.base import BaseController

import ckan.lib.jsonp as jsonp
import ckanext.s3multipart.plugin as plugin


class S3MultipartController(BaseController):
    @jsonp.jsonpify
    def s3_auth(self, dataset):
        return plugin.get_session_credentials(dataset)

    @jsonp.jsonpify
    def s3_post(self, dataset):
        return plugin.get_presigned_post(dataset)