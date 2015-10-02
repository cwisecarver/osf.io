'use strict';
/**
 * API client for the 'nodes' resource.
 *
 * Usage:
 *
 *    var client = new NodeClient();
 *    client.list({pageSize: 100}).then(function(nodes) {
 *        nodes.forEach(function(node) {
 *            console.log(node.title);
 *            console.log(node.description);
 *        })
 *    });
 *
 *    client.detail('abc12').then(function(node) {
 *        console.log('Information about Node abc12:');
 *        console.log(node.title);
 *        console.log(node.isPublic);
 *    });
 */
var base = require('js/resources/base');
var oop = require('js/oop');
var $ = require('jquery');

/** Node model */
var NodeInstance = $.extend(base.BaseModel, {
    name: 'Node'
});

var NodeClient = oop.extend(base.BaseClient, {
    model: NodeInstance,
    path_segment: 'nodes',
    name: 'node'
});

module.exports = {
    Node: NodeInstance,
    NodeClient: NodeClient
};
