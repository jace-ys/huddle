// See https://github.com/dialogflow/dialogflow-fulfillment-nodejs
// for Dialogflow fulfillment library docs, samples, and to report issues
'use strict';

var request = require('request');

let trello_key = '9699a11bcd760a9dd78e59338314e870';
let trello_token = '01aeff8a98124ef0e63130c2c44a34284be6df1f604c427e17b603a3ae78d6b1';

let to_do_list_id = '5bbe27fb23dadc12a98e2cb6';
let doing_list_id = '5bca6606e9755b36abcd041e';
let done_list_id = '5bbe28035d22ed6a690fdabe';


function discuss_to_do() {
    var task = context.parameters.task;
    var card_id = find_card(task);
    if (card_id != "error") {
    console.log(card_id);
    update_card(card_id, to_do_list_id);
    } else {
    create_card(task, to_do_list_id);
    }
    console.log(`Moving ` + task + ` to to-do`);
}

function discuss_doing() {
    var task = context.parameters.task;
    var card_id = find_card(task);
    if (card_id != "error") {
    update_card(card_id, doing_list_id);
    } else {
    create_card(task, doing_list_id);
    }
    console.log(`Moving ` + task + ` to doing`);
}

function discuss_done() {
    var task = context.parameters.task;
    var card_id = find_card(task);
    if (card_id != "error") {
    update_card(card_id, done_list_id);
    } else {
    create_card(task, done_list_id);
    }
    console.log(`Moving ` + task + ` to done`);
}

function to_do() {
    var task = parameters.task;
    var card_id = find_card(task);
    if (card_id != "error") {
    update_card(card_id, to_do_list_id);
    } else {
    create_card(task, to_do_list_id);
    }
    console.log(`Moving ` + task + ` to to-do`);
}

function doing() {
    var task = parameters.task;
    var card_id = find_card(task);
    if (card_id != "error") {
    update_card(card_id, doing_list_id);
    } else {
    create_card(task, doing_list_id);
    }
    console.log(`Moving ` + task + ` to doing`);
}

function done() {
    var task = parameters.task;
    var card_id = find_card(task);
    if (card_id != "error") {
    update_card(card_id, done_list_id);
    } else {
    create_card(task, done_list_id);
    }
    console.log(`Moving ` + task + ` to done`);
}

function find_card(task) {
    var options = { method: 'GET',
        url: 'https://api.trello.com/1/search',
        qs: { query: 'name:'+task, key: trello_key, token: trello_token } 
    };
    request(options, function (error, response, body) {
        if (JSON.parse(body).cards.length !== 0) {
            console.log(body);
            return JSON.parse(body).cards[0].id;
        } else {
            return "error";
        }
    });
}
function update_card(card_id, list_id) {
    var options = {method: 'PUT',
        url: 'https://api.trello.com/1/cards/' + card_id,
        qs: { idList: list_id, key: trello_key, token: trello_token } 
    };
    request(options, function (error, response, body) {
        if (error) throw new Error(error);
        else {
            console.log(body);
        }
    });
}

function create_card(task, list_id){
    var options = { method: 'POST',
        url: "https://api.trello.com/1/cards",
        qs: { name: task, idList: list_id, keepFromSource: "all", key: trello_key, token: trello_token }
    };
    request(options, function (error, response, body) {
        if (error) throw new Error(error);
        else {
            console.log(body);
        }
    });
}