# ckanext-s3multipart

An extension to allow client-side multipart uploads of files to Amazon
S3. This allows 4 concurrent uploads of 5mb parts of a large file with
retrying of failed parts as well as file upload progress.

Access to S3 is only made available with temporary 60 minute AWS API
keys to users with CKAN access to create packages.

## Requirements

"boto3" python library

Amazon Web Services account for S3 API usage

## Installation

To install ckanext-s3multipart:

1.  Activate your CKAN virtual environment, for example:

        . /usr/lib/ckan/default/bin/activate

2.  Install the ckanext-s3multipart Python package into your virtual
    environment:

        git clone https://github.com/maxious/ckanext-s3multipart.git
        cd ckanext-s3multipart
        python setup.py develop
        pip install -r dev-requirements.txt

3.  Add `s3multipart` to the `ckan.plugins` setting in your CKAN config
    file (by default the config file is located at
    `/etc/ckan/default/production.ini`).
4.  Create an s3 bucket and set Bucket Name and Region in CKAN config
    file

​5. You need to allow CORS access to your bucket
<https://docs.aws.amazon.com/AWSJavaScriptSDK/guide/browser-configuring.html#Configuring_CORS_for_an_Amazon_S3_Bucket>
Make sure your CORS settings for your S3 bucket looks similar to what is
provided below (The PUT allowed method and the ETag exposed header are
critical).

    <?xml version="1.0" encoding="UTF-8"?>
    <CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
        <CORSRule>
            <AllowedOrigin>https://*.yourdomain.com</AllowedOrigin>
            <AllowedOrigin>http://*.yourdomain.com</AllowedOrigin>
            <AllowedMethod>PUT</AllowedMethod>
            <AllowedMethod>POST</AllowedMethod>
            <AllowedMethod>DELETE</AllowedMethod>
            <MaxAgeSeconds>3000</MaxAgeSeconds>
            <ExposeHeader>x-amz-version-id</ExposeHeader>
            <ExposeHeader>ETag</ExposeHeader>
            <AllowedHeader>*</AllowedHeader>
        </CORSRule>
        <CORSRule>
            <AllowedOrigin>*</AllowedOrigin>
            <AllowedMethod>GET</AllowedMethod>
            <AllowedHeader>*</AllowedHeader>
        </CORSRule>
    </CORSConfiguration>

​5. Create an S3 access policy. For maximum security, rather than using
the Amazon managed policies, create a custom IAM policy. You should also
insert the name of your bucket in the resource clause to further limit
access eg. "Resource": "arn:aws:s3:::bucketname/\*" (Remove any spaces
before the first bracket after copying)

	 {
	    "Version": "2012-10-17", "Statement": [ { "Effect": "Allow",
	     "Action": [ "s3:GetObject\*", "s3:GetBucketLocation",
	     "s3:PutObject\*", "s3:\*Multipart\*" ], "Resource": "\*" } ]
	
	 }

​6. Setup an s3 access only IAM role
<https://console.aws.amazon.com/iam/home> The type of role is "Role for
Cross-Account Access -\> Provide access between AWS accounts you own"
(the account will be accessing itself) You'll need your 12 digit Amazon
Account ID from the Billing Information control panel
<https://console.aws.amazon.com/billing/home> Then create add the role
name to the ckan config file

​6. Set up a IAM user with the S3 access policy and also AWS Security
Token Service access to AssumeRole. You should also insert the name of
the IAM role in the resource clause to further limit access eg.

	"Resource": "arn:aws:iam::1234:role/S3MultipartUploadOnly" { 
		"Version": "2012-10-17", 
		"Statement": 
		[ { "Effect": "Allow", 
		"Action": "sts:AssumeRole", 
		"Resource": "\*" } ]
	 }

Make those credentials available to "boto" the python library for AWS eg. by creating environment variables AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
<https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration>

7.  Restart CKAN. For example if you've deployed CKAN with Apache on
    Ubuntu:

        sudo service apache2 reload

Config Settings
===============

    # S3 bucket name 
    ckanext.s3multipart.s3_bucket = bucket_name 
    # S3 region eg. ap-southeast-2 
    ckanext.s3multipart.s3_region = region_name 
    # S3 IAM role ARN eg. "arn:aws:iam::$account-id:role/$role-name" 
    ckanext.s3multipart.s3_role = arn:aws:iam::1234:role/S3MultipartUploadOnly

TODOs
=====
Additional Key Value metadata including original portal, user, package
and resource id when uploaded via JS

Limit file upload size using IAM policy on content-length headers?

