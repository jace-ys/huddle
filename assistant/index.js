// See https://github.com/dialogflow/dialogflow-fulfillment-nodejs
// for Dialogflow fulfillment library docs, samples, and to report issues
'use strict';
 
const functions = require('firebase-functions');
const {WebhookClient} = require('dialogflow-fulfillment');
const {Card, Suggestion} = require('dialogflow-fulfillment');
var request = require('request');
 
let trello_host = 'https://api.trello.com/1';
let trello_key = '9699a11bcd760a9dd78e59338314e870';
let trello_token = '01aeff8a98124ef0e63130c2c44a34284be6df1f604c427e17b603a3ae78d6b1';

let to_do_list_id = '5bbe27fb23dadc12a98e2cb6';
let doing_list_id = '5bca6606e9755b36abcd041e';
let done_list_id = '5bbe28035d22ed6a690fdabe';


process.env.DEBUG = 'dialogflow:debug'; // enables lib debugging statements

exports.dialogflowFirebaseFulfillment = functions.https.onRequest((request, response) => {
  const agent = new WebhookClient({ request, response });
  console.log('Dialogflow Request headers: ' + JSON.stringify(request.headers));
  console.log('Dialogflow Request body: ' + JSON.stringify(request.body));
  console.log(request.body.queryResult);
  let parameters = request.body.queryResult.parameters;
  let context = request.body.queryResult.outputContexts[0];
 
  function welcome(agent) {
    agent.add(`Hi! I am Huddle, your team's personal virtual secretary. Push the button to begin the huddle.`);
  }
 
  function fallback(agent) {
    agent.add(`I didn't understand`);
    agent.add(`I'm sorry, can you try again?`);
}

  function discuss_to_do(agent) {
      var task = context.parameters.task;
      find_card(task).then((output)=> {
          if (output != "not found"){
              console.log("card not found");
          } else {
              console.log("card found");
          }
      }
      agent.add(`Moving ` + task + ` to to-do`);
  }


  // Run the proper function handler based on the matched Dialogflow intent name
  let intentMap = new Map();
  intentMap.set('Default Welcome Intent', welcome);
  intentMap.set('Default Fallback Intent', fallback);
  intentMap.set('discuss-task: to-do', discuss_to_do);
  intentMap.set('discuss-task: doing', discuss_doing);
  intentMap.set('discuss-task: done', discuss_done);
  intentMap.set('to-do', to_do);
  intentMap.set('doing', doing);
  intentMap.set('done', done);
  // intentMap.set('your intent name here', yourFunctionHandler);
  // intentMap.set('your intent name here', googleAssistantHandler);
  agent.handleRequest(intentMap);
});

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

function find_card (task) {
    return new Promise((resolve, reject) => {
      // Create the path for the HTTP request to get the weather
      let path = '/search?query=name:' + task + '&key=' + trello_key + '&token=' + trello_token;
      console.log('API Request: ' + trello_host + path);
      // Make the HTTP request to get the weather
      http.get({host: trello, path: path}, (res) => {
        let body = ''; // var to store the response chunks
        res.on('data', (d) => { body += d; }); // store each response chunk
        res.on('end', () => {
          // After all the data has been received parse the JSON for desired data
          let response = JSON.parse(body);
          if (response.cards.length !== 0){
            let card_id = response.cards[0].id;
          } else {
            let card_id = "not found";
          }
          // Resolve the promise with the output text
          console.log(card_id);
          resolve(output);
        });
        res.on('error', (error) => {
          reject(error);
        });
      });
    });
  }