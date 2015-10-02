'use strict';
/**
 * API client for the 'users' resource.
 *
 * Usage:
 *
 *    var client = new UserClient();
 *    client.list({pageSize: 100}).then(function(users) {
 *        users.forEach(function(user) {
 *            console.log(user.title);
 *            console.log(user.description);
 *        })
 *    });
 *
 *    client.detail('abc12').then(function(user) {
 *        console.log('Information about User abc12:');
 *        console.log(user.title);
 *        console.log(user.isPublic);
 *    });
 */
var base = require('js/resources/base');
var oop = require('js/oop');
var $ = require('jquery');

/** User model */
var User = $.extend(base.BaseModel, {
    name: 'User'
});

var UserClient = oop.extend(base.BaseClient, {
    model: User,
    path_segment: 'users',
    name: 'user'
});

module.exports = {
    User: User,
    UserClient: UserClient
};
