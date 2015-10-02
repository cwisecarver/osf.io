'use strict';

var Raven = require('raven-js');
var URI = require('URIjs');
var oop = require('js/oop');
var $ = require('jquery');

var BaseModel = oop.defclass({  // jshint ignore:line
    /** Params is the data from the server. */
    name: null,
    constructor: function Constructor(params) {
        jsonAPISmartExtend(true, this, params);
    },
    toString: function ToString() {
        return '[' + this.name + ' ' + this.id + ']';
    }
});


var jsonAPISmartExtend = function JSONAPISmartExtend() {
    // Mostly borrowed from jQuery.extend with things to enhance the objects
    // based on aspects of the JSON-API schema.

    var options, name, src, copy, copyIsArray, clone,
    target = arguments[0] || {},
    i = 1,
    length = arguments.length,
    deep = false;

  // Handle a deep copy situation
  if (typeof target === 'boolean') {
    deep = target;

    // Skip the boolean and the target
    target = arguments[i] || {};
    i++;
  }

  // Handle case when target is a string or something (possible in deep copy)
  if (typeof target !== 'object' && !$.isFunction(target)) {
    target = {};
  }

  // Extend jQuery itself if only one argument is passed
  if (i === length) {
    target = this;
    i--;
  }

  for (; i < length; i++) {

    // Only deal with non-null/undefined values
    if ((options = arguments[i]) != null) {

      // Extend the base object
      for (name in options) {
        src = target[name];
        copy = options[name];

        // Prevent never-ending loop
        if (target === copy) {
          continue;
        }

        // Recurse if we're merging plain objects or arrays
        if (deep && copy && ($.isPlainObject(copy) ||
          (copyIsArray = $.isArray(copy)))) {

          if (copyIsArray) {
            copyIsArray = false;
            clone = src && $.isArray(src) ? src : [];

          } else {
            clone = src && $.isPlainObject(src) ? src : {};
          }

          // Never move original objects, clone them
          target[name] = jsonAPISmartExtend(deep, clone, copy);
          // try and lazily hydrate api urls
        } else if ($.type(copy) === 'string' && copy !== '') {
          var matches = copy.match(/http:\/\/.*\/v2\/(.*)\//);
          if (matches) {
            var apiClientOptions = {
              'model': BaseModel,
              'name': matches[1],
              'path_segment': matches[1]
            };
            console.log('Hydrated ', name, copy, ' as a API url looking like ', apiClientOptions.path_segment);
            target[name] = new BaseClient(apiClientOptions);
          } else {
            target[name] = copy;
          }
        // Don't bring in undefined values
        } else if (copy !== undefined) {
          target[name] = copy;
        }
      }
    }
  }

  // Return the modified object
  return target;
};

var BaseClient = oop.defclass({
    DEFAULT_AJAX_OPTIONS: {
        contentType: 'application/vnd.api+json',
        dataType: 'json',
        xhrFields: {
          withCredentials: true
        }
    },
    constructor: function(options) {
      options = options || {};
      this.model = options.model || null;
      this.path_segment = options.path_segment || null;
      this.name = options.name || null;
      if(!(this.model || this.path_segment || this.name)) {
        return false;
      }
    },
    model: null,
    path_segment: null,
    name: null,
    detail: function(params) {
        params = params || {};
        var id = params.id;
        var ret = $.Deferred();
        var Model = this.model;
        this._request({url: '/'+this.path_segment+'/'+id+'/'})
            .done(function handleResonse(resp) {
                    console.log('API Returned: ', resp);
                    var user = new Model(resp.data);
                    ret.resolve(user);
                })
            .fail(captureError('Could not fetch individual ' + this.name + '.'));
        return ret.promise();
    },
    list: function(params) {
        /**
         * Return a promise that resolves to an Array of this.model objects.
         * @param {object} params
         *  {number} pageSize
         */
         var listingQSParams = {
             pageSize: 'page[size]',
             // TODO: Support filtering and other querystring enabled features.
         };
        params = params || {};
        var ret = $.Deferred();
        var queryStringObject = {};
        for(var key in params) {
            if(listingQSParams.hasOwnProperty(key)) {
                queryStringObject[listingQSParams[key]] = params[key];
            }
        }

        var Model = this.model;
        this._request({
                url: '/'+this.path_segment+'/',
                query: queryStringObject
            })
            .done(function handleResponse(resp) {
              console.log('API Returned: ', resp);
              var items = $.map(resp.data, function instantiateItem(data) {
                  return new Model(data);
              });

              ret.resolve($.extend(resp, {'data': items}));
            }).fail(captureError('Could not fetch ' + this.name + ' list.'));

        return ret.promise();
    },
    /**
     * Make an API request.
     * NOTE: Assumes request bodies are JSON.
     *
     * @param {object} params
     *  {string} method
     *  {string} url
     *  {object} query
     *  {object} data: Request body (will be JSONified)
     *  {object} options: Additional options to pass to $.ajax
     */
    _request: function(params) {
        var baseUrl = $.osf.apiV2Url(params.url, {});
        var uri = URI(baseUrl)
            .query(params.query || {}).toString();
        var jsonData = JSON.stringify(params.data || {});
        console.log('requested ', uri);
        var opts = $.extend(
            {},
            {
                url: uri,
                data: jsonData,
                type: params.method || 'GET',
            },
            this.DEFAULT_AJAX_OPTIONS,
            params.options
        );
        return $.ajax(opts);
    },
});

/**
 * Return a generic error handler for requests.
 * Log to Sentry with the given message.
 *
 * Usage:
 *     client.makeRequest()
 *          .fail(captureError('Failed to make request'));
 */
var DEFAULT_ERROR_MESSAGE = 'Request failed.';
function captureError(message, callback) {
    return function(xhr, status, error) {
        Raven.captureMessage(message || DEFAULT_ERROR_MESSAGE, {
            xhr: xhr, status: status, error: error
        });
        // Additional error-handling
        callback && callback(xhr, status, error);
    };
}

module.exports = {
    BaseClient: BaseClient,
    BaseModel: BaseModel,
    captureError: captureError
};
