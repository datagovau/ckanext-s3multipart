=============
ckanext-s3multipart
=============

An extension to allow client-side multipart uploads of files to Amazon S3.
This allows 4 concurrent uploads of 5mb parts of a large file with retrying of failed parts
as well as file upload progress.

Access to S3 is only made available with temporary 60 minute AWS API keys to users with CKAN access to create packages.

------------
Requirements
------------

"boto" python library

Amazon Web Services account for S3 API usage

------------
Installation
------------

To install ckanext-s3multipart:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-s3multipart Python package into your virtual environment::

     pip install ckanext-s3multipart

3. Add ``s3multipart`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Set Bucket Name and Region in config file

5. You need to allow CORS access to your bucket https://docs.aws.amazon.com/AWSJavaScriptSDK/guide/browser-configuring.html#Configuring_CORS_for_an_Amazon_S3_Bucket

6. Set up a IAM user with S3 access only and make those credentials available to "boto" the python library for AWS https://boto.readthedocs.org/en/latest/boto_config_tut.html

7. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


---------------
Config Settings
---------------

Document any optional config settings here. For example::

    # The minimum number of hours to wait before re-checking a resource
    # (optional, default: 24).
    ckanext.s3multipart.s3_bucket = bucket_name
    ckanext.s3multipart.s3_region = region_name

------------------------
Development Installation
------------------------

To install ckanext-s3multipart for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/maxious/ckanext-s3multipart.git
    cd ckanext-s3multipart
    python setup.py develop
    pip install -r dev-requirements.txt


