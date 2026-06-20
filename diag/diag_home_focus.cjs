#!/usr/bin/env node
// Generic home-focus snapshot. Reports the active element, .gpfocus,
// .gpfocuswithin presence and doc.hasFocus() in the chosen target.
// Useful to diagnose "no focus / body has focus" cold-boot pathology.
//
// Usage: node diag_home_focus.cjs [<title-substring>]
// Default title-substring is 'Big Picture'.
'use strict';

var ws = require('ws');
var http = require('http');

var HOST = process.env.DECK_CDP_HOST || process.env.DECK_HOST || '127.0.0.1';
var PORT = process.env.DECK_CDP_PORT || '8081';
var TITLE = (process.argv[2] || 'Big Picture').toLowerCase();

http.get({ host: HOST, port: PORT, path: '/json' }, function(res) {
  var body = '';
  res.on('data', function(d) { body += d; });
  res.on('end', function() {
    var targets;
    try { targets = JSON.parse(body); } catch (e) { console.error('parse failed:', e.message); process.exit(2); }
    var match = targets.find(function(t) { return (t.title || '').toLowerCase().indexOf(TITLE) >= 0; });
    if (!match) {
      console.error('No target matching:', TITLE);
      console.error('Available:', targets.map(function(t) { return t.title; }).join(', '));
      process.exit(2);
    }
    var wsurl = (match.webSocketDebuggerUrl || '').replace('wss://', 'ws://');
    var client = new ws(wsurl);
    var msgId = 1;
    function send(method, params, cb) {
      var id = msgId++;
      var handler = function(data) {
        var msg = JSON.parse(data);
        if (msg.id === id) { client.removeListener('message', handler); cb(null, msg.result); }
      };
      client.on('message', handler);
      client.send(JSON.stringify({ id: id, method: method, params: params || {} }));
    }
    var expr = `JSON.stringify((function() {
      function info(el) {
        if (!el) return null;
        var r = el.getBoundingClientRect();
        return {
          tag: el.tagName, id: el.id || null,
          cls: typeof el.className === 'string' ? el.className.slice(0, 200) : '',
          dataAppid: el.getAttribute('data-appid') || null,
          top: Math.round(r.top), height: Math.round(r.height), width: Math.round(r.width),
        };
      }
      var active = document.activeElement;
      var gpfocus = document.querySelector('.gpfocus');
      var gpfocusWithin = document.querySelectorAll('.gpfocuswithin');
      return {
        activeElement: info(active),
        gpfocus: info(gpfocus),
        gpfocusWithinCount: gpfocusWithin.length,
        gpfocusWithinSample: Array.from(gpfocusWithin).slice(0, 3).map(info),
        bodyHasFocus: document.body === active,
        docHasFocus: document.hasFocus(),
      };
    })())`;
    client.on('open', function() {
      send('Runtime.evaluate', { expression: expr, returnByValue: true }, function(_e, result) {
        var v = result && result.result && result.result.value;
        try { console.log(JSON.stringify(JSON.parse(v), null, 2)); } catch (e) { console.log(v); }
        client.close();
      });
    });
    client.on('error', function(e) { console.error('ERR:' + e.message); process.exit(1); });
    setTimeout(function() { process.exit(1); }, 15000);
  });
}).on('error', function(err) { console.error('list-targets failed:', err.message); process.exit(2); });
