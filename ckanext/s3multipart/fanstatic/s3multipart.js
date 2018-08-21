"use strict";

ckan.module('s3multipart', function ($) {
  return {
    initialize: function () {

      var s3_enabled = false;
      var isInChoose = false;

      var accessKeyId = this.options.accesskeyid;
      var secretAccessKey = this.options.secretaccesskey;
      var sessionToken = this.options.sessiontoken;
      var region = this.options.region;
      var bucket = this.options.bucket;
      var prefix = this.options.prefix;

      $.proxyAll(this, /_on/);
      // https://jsfiddle.net/embkay06/kjjcv42L/32/
      $(window).on("focus", function (temp) {
        if (isInChoose) {
          isInChoose = false;
          setTimeout(function () {
            temp = $("#field-image-upload").val();
            if (temp) {
              return;
            }
            s3_enabled = false;
          }, 500);
        }
      });
      $('#field-image-upload').change(function (evt) {
        var files = evt.target.files;
        if (files.length == 0) {
          s3_enabled = false;
        }
        if (s3_enabled) {
          var s3 = new AWS.S3({
            accessKeyId: accessKeyId,
            secretAccessKey: secretAccessKey,
            sessionToken: sessionToken,
            region: region
          });
          // https://docs.aws.amazon.com/AWSJavaScriptSDK/latest/AWS/S3/ManagedUpload.html
          // default = 4 concurrent uploads of 5mb parts
          var managedUpload = s3.upload({
            ACL: 'public-read',
            Body: files[0],
            Bucket: bucket,
            Key: prefix + files[0].name
          }, function (error, data) {
            // upload finished
            if (error) {
              // upload failed
              $('.meter').hide();
              $('#upload-progress').html('Upload failed due to error:' + data);
              console.log(data);
            }
            else if (data) {
              // upload succeeded
              $('.meter').hide();
              $('#upload-progress').html('Upload completed, file available at <a href="' + data['Location']
                  + '">' + data['Location'] + '</a>');

              $('#field-image-url').attr('value', data['Location']).attr('placeholder', data['Location']);
              $('#field-image-url')[0].value = data['Location'];

            }
          });

          managedUpload.on('httpUploadProgress', function (progress) {
            // progress event handler
            // progress.loaded = number of bytes uploaded so far
            $('.meter').show().first().children().width(Math.round(progress.loaded / progress.total * 100) + '%');
            $('#upload-progress').html(
                Math.round(progress.loaded / progress.total * 100)
                + '% uploaded (' + progress.loaded + ' of ' + progress.total + ' bytes)');
          });

          $('.btn-remove-url').on('click', function () {
            s3_enabled = false;
            managedUpload.abort();
          });
          $(evt.target).val('');
        }
        ;
      });
      $("#advanced-upload").show().on('click', function () {
        s3_enabled = true;
        isInChoose = true;

        $('#field-image-upload').click();

      })
      //$("#field-image-upload").hide();
    }

  }
});
