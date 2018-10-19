const express = require('express');
const app = express();
const server = require('http').createServer(app);
const XMLHttpRequest = require('xmlhttprequest').XMLHttpRequest;

var bodyParser = require('body-parser');
app.use(bodyParser.json()); // to support JSON-encoded bodies
app.use(bodyParser.urlencoded({ // to support URL-encoded bodies
  extended: true
}));

// Get process.env variables
require('dotenv').config();

const port = 3000;
server.listen(port);

const api_key_str = "key=" + process.env.TRELLO_KEY + "&token=" + process.env.TRELLO_TOKEN;

var cards = [{}];
var lists = [{}];
var card_ready = false;
var list_ready = false;

xhttp = new XMLHttpRequest();
xhttp.onreadystatechange = function() {
  if (this.readyState == 4 && this.status == 200) {
    cards = JSON.parse(this.responseText);
    card_ready = true;
  }
};
// Open Connection
xhttp.open("GET", "https://api.trello.com/1/boards/" + process.env.BOARD_ID + "/cards?fields=name,id&" + api_key_str , true);
// Send the HTTP request
xhttp.send();

xhttp1 = new XMLHttpRequest();
xhttp1.onreadystatechange = function() {
  if (this.readyState == 4 && this.status == 200) {
    lists = JSON.parse(this.responseText);
    list_ready = true;
  }
};
// Open Connection
xhttp1.open("GET", "https://api.trello.com/1/boards/" + process.env.BOARD_ID + "/lists?" + api_key_str , true);
// Send the HTTP request
xhttp1.send();

app.post('/api/update', function(req, res) {
  while (!(card_ready && list_ready)) {

  }
  var task = req.body.task;
  var destination = req.body.destination;
  var updated = false;
  var card_found = false;

  for (i = 0; i < cards.length; i++) {
    // If card with given kame found
    if (cards[i]["name"] === task) {
      card_found = true;
      for (j = 0; j < lists.length; j++) {
        // If card with given kame found
        if (lists[j]["name"] === destination) {
          updated = true;
          var xhttp = new XMLHttpRequest();
          // Open Connection
          xhttp.open("PUT", "https://api.trello.com/1/cards/" + cards[i]["id"] + "?idList=" + lists[j]["id"] + "&" + api_key_str , true);
          // Send the HTTP request
          xhttp.send();
          res.send(200);
        }
        break;
      }
      // If List with given name not found
      if (!updated) {
        updated = true;
        var xhttp1 = new XMLHttpRequest();
        xhttp1.onreadystatechange = function() {
          if (this.readyState == 4 && this.status == 200) {
            var response = JSON.parse(this.responseText);
            var xhttp2 = new XMLHttpRequest();
            // Open Connection
            xhttp2.open("PUT", "https://api.trello.com/1/cards/" + cards[i]["id"] + "?idList=" + response["id"] + "&" + api_key_str , true);
            // Send the HTTP request
            xhttp2.send();
            res.send(200);
          }
        };
        // Open Connection
        xhttp1.open("POST", "https://api.trello.com/1/boards/" + process.env.BOARD_ID + "/lists?name=" + destination + "&pos=top&" + api_key_str , true);
        // Send the HTTP request
        xhttp1.send();
      }
      break;
    }
  }

  // If Card with given name not found
  if (!card_found) {
    for (j = 0; j < lists.length; j++) {
      // If card with given kame found
      if (lists[j]["name"] === destination) {
        updated = true;
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function() {
          if (this.readyState == 4 && this.status == 200) {
            res.send(200);
          }
        };
        // Open Connection
        xhttp.open("POST", "https://api.trello.com/1/cards?name=" + task + "&idList=" + lists[j]["id"] + "&keepFromSource=all&" + api_key_str , true);
        // Send the HTTP request
        xhttp.send();
        break;
      }
    }
    // If List with given name not found
    if (!updated) {
      var xhttp1 = new XMLHttpRequest();
      xhttp1.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
          var response = JSON.parse(this.responseText);
          var xhttp2 = new XMLHttpRequest();
          xhttp2.onreadystatechange = function() {
            if (this.readyState == 4 && this.status == 200) {
              res.send(200);
            }
          };
          // Open Connection
          xhttp2.open("POST", "https://api.trello.com/1/cards?name=" + task + "&idList=" + response["id"] + "&keepFromSource=all&" + api_key_str , true);
          // Send the HTTP request
          xhttp2.send()
        }
      };
      // Open Connection
      xhttp1.open("POST", "https://api.trello.com/1/boards/" + process.env.BOARD_ID + "/lists?name=" + destination + "&pos=top&" + api_key_str , true);
      // Send the HTTP request
      xhttp1.send();
    }
  }
});
