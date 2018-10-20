const axios = require("axios");

let trello_key = '9699a11bcd760a9dd78e59338314e870';
let trello_token = '01aeff8a98124ef0e63130c2c44a34284be6df1f604c427e17b603a3ae78d6b1';

let to_do_list_id = '5bbe27fb23dadc12a98e2cb6';
let doing_list_id = '5bca6606e9755b36abcd041e';
let done_list_id = '5bbe28035d22ed6a690fdabe';

const findCard = (task) => {
  axios.get('https://api.trello.com/1/search', {
      params: { query: 'name:'+task, key: trello_key, token: trello_token }
    }).then(response => {
      if (response.data.cards.length) {
        console.log(response.data.cards[0].id);
        return response.data.cards[0].id;
      } else {
        throw new Error("Unable to find card");
      }
    }).catch(err => {
      console.log(error);
    });
}

const createCard = (task) => {

}

const updateCard = (task) => {

}

findCard("python");
