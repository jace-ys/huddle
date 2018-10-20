import requests
import json

map_id = {
  "to-do": '5bbe27fb23dadc12a98e2cb6',
  "doing": '5bca6606e9755b36abcd041e',
  "done": '5bbe28035d22ed6a690fdabe'
}

key = "9699a11bcd760a9dd78e59338314e870"
token = "01aeff8a98124ef0e63130c2c44a34284be6df1f604c427e17b603a3ae78d6b1"

def find_card (task, destination):
  # Link of serach for trello API
  url = "https://api.trello.com/1/search"

  # Params of search
  querystring = {
    "query":"is:open name:" + task,
    "idBoards":"5bbe266d9eb33189e0c31011",
    "modelTypes":"cards",
    "card_fields":"name,id",
    "key":key,
    "token":token
  }

  # Send HTTP request
  response = requests.request("GET", url, params=querystring)

  # Parse the JSON
  cards = json.loads(response.text)["cards"]

  if (len(cards) != 0): 
    card_id = cards[0]["id"]
    update_card(card_id, map_id[destination])
  else:
    create_card(task, map_id[destination])
    card_id = "not found"

def update_card(card_id, list_id):
  url = "https://api.trello.com/1/cards/" + card_id

  # Params of search
  querystring = {
    "idList":list_id,
    "key":key,
    "token":token
  }
  # Send HTTP request
  response = requests.request("PUT", url, params=querystring)
  print(response)

def create_card(task, list_id):
  url = "https://api.trello.com/1/cards"

  # Params of search
  querystring = {
    "name":task,
    "idList":list_id,
    "keepFromSourc":"all",
    "key":key,
    "token":token
  }
  # Send HTTP request
  response = requests.request("POST", url, params=querystring)
