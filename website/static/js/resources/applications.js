'use strict';
/**
 * API client for the 'applications' resource.
 *
 * Usage:
 *
 *    var client = new ApplicationClient();
 *    client.list({pageSize: 100}).then(function(applications) {
 *        applications.forEach(function(application) {
 *            console.log(application.title);
 *            console.log(application.description);
 *        })
 *    });
 *
 *    client.detail('abc12').then(function(application) {
 *        console.log('Information about Application abc12:');
 *        console.log(application.title);
 *        console.log(application.isPublic);
 *    });
 */
var base = require('js/resources/base');
var oop = require('js/oop');
var $ = require('jquery');

/** Application model */
var Application = oop.extend(base.BaseModel, {
    name: 'Application'
});

var ApplicationClient = oop.extend(base.BaseClient, {
    model: Application,
    path_segment: 'applications',
    name: 'application'
});

module.exports = {
    Application: Application,
    ApplicationClient: ApplicationClient
};
