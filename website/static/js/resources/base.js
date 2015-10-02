'use strict';

var Raven = require('raven-js');
var URI = require('URIjs');
var oop = require('js/oop');
var $ = require('jquery');

var BaseModel = oop.defclass({  // jshint ignore:line
    /** Params is the data from the server. */
    name: null,
    constructor: function userConstructor(params) {
        $.extend(this, params);
    },
    toString: function userToString() {
        return '[' + this.name + ' ' + this.id + ']';
    }
});

var BaseClient = oop.defclass({
    DEFAULT_AJAX_OPTIONS: {
        contentType: 'application/vnd.api+json',
        dataType: 'json'
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
                var items = $.map(resp.data, function instantiateItem(data) {
                    return new Model(data);
                });
                ret.resolve(items);
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
