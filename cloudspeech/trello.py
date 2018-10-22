import requests
import json
import urllib

map_id = {
  "to-do": '5bbe27fb23dadc12a98e2cb6',
  "doing": '5bca6606e9755b36abcd041e',
  "done": '5bbe28035d22ed6a690fdabe',
  "": None
}

map_member = {
    "Rachel": "5bb699ba52c2ff0433d2d70b",
    "rachel": "5bb699ba52c2ff0433d2d70b",
    "Mark": "5b70e363e51b481792ebef7c",
    "mark": "5b70e363e51b481792ebef7c",
    "Jace": "5b2a8b92d443055bce5e1517",
    "jace": "5b2a8b92d443055bce5e1517",
    "Joan": "5bb347f591731d3c5fd84717",
    "joan": "5bb347f591731d3c5fd84717",
    "": None
}

def find_card (term, card_title, destination, due_date, member):
  # Link of serach for trello API
  url = "https://api.trello.com/1/search"

  # Params of search
  querystring = {
    "query":"is:open name:"+term,
    "partial":"true",
    # "idBoards":"5bbe266d9eb33189e0c31011",
    # "modelTypes":"cards",
    # "card_fields":"name,id"
    "key":key,
    "token":token
  }

  # Send HTTP request
  response = requests.request("GET", url, params=querystring)

  print(response.text)
  # Parse the JSON
  cards = json.loads(response.text)["cards"]

  if (len(cards) != 0):
    card_id = cards[0]["id"]
    # print("found card")
    update_card(card_id, card_title, map_id[destination], due_date, map_member[member])
  else:
    # print("card not found")
    create_card(card_title, map_id[destination], due_date, map_member[member])
    card_id = "not found"

def update_card(card_id, card_title, list_id, due_date, member_id):
  url = "https://api.trello.com/1/cards/" + card_id

  # Params of search
  querystring = {
    "name": card_title,
    "key":key,
    "token":token
  }

  # Set custom params
  if (list_id):
    querystring["idList"] = list_id
  if (due_date != ""):
    querystring["due"] = due_date
  if (member_id):
    print(member_id)
    querystring["idMembers"] = member_id

  print(querystring)
  # Send HTTP request
  response = requests.request("PUT", url, params=querystring)
  print(response)

def create_card(card_title, list_id, due_date, member_id):
  url = "https://api.trello.com/1/cards"

  # Params of search
  querystring = {
    "name":card_title,
    "keepFromSourc":"all",
    "key":key,
    "token":token
  }

  # Set custom params
  if (list_id):
    querystring["idList"] = list_id
  if (due_date != ""):
    querystring["due"] = due_date
  if (member_id):
    querystring["idMembers"] = member_id

  # print(querystring)
  # Send HTTP request
  response = requests.request("POST", url, params=querystring)
  # print(response)
