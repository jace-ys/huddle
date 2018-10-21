#!/usr/bin/env python3
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A demo of the Google CloudSpeech recognizer."""


import logging
from threading import Thread, Event
import threading
import signal
import time
from queue import Queue

import requests

import aiy.audio
import aiy.cloudspeech
import aiy.voicehat
import dialogflow_v2 as dialogflow

session_client = dialogflow.SessionsClient()

session = session_client.session_path("project-huddle", "1231")
print('Dialogflow session path: {}\n'.format(session))

# initialise instances of app objects
text_queue = Queue()
trello_queue = Queue()

trello_key="9699a11bcd760a9dd78e59338314e870"
trello_token="01aeff8a98124ef0e63130c2c44a34284be6df1f604c427e17b603a3ae78d6b1"
trello_board_id="5bbe266d9eb33189e0c31011"
trello_host = "https://api.trello.com/1/"

def signal_handler(signal, frame):
    """ Ctrl+C handler to cleanup """
    for t in threading.enumerate():
        print(t)
        if t.name != 'MainThread':
            t.shutdown_flag.set()

    print('Goodbye!')
    sys.exit(1)

class HuddleThread(Thread):
    def __init__(self, text_queue):
        Thread.__init__(self)
        self.text_queue = text_queue
        self.shutdown_flag = Event()

    def run(self):
        recognizer = aiy.cloudspeech.get_recognizer()
        aiy.audio.get_recorder().start()

        while True:
            print('Listening...')
            text = recognizer.recognize()
            if text:
                print('You said "', text, '"')
                text_queue.put(text)

class DialogflowThread(Thread):
    def __init__(self, text_queue):
        Thread.__init__(self)
        self.text_queue = text_queue
        self.shutdown_flag = Event()

    def run(self):
        """Returns the result of detect intent with texts as inputs.

        Using the same `session_id` between requests allows continuation
        of the conversaion."""
        while not self.shutdown_flag.is_set():
            if self.text_queue.not_empty():
                text = self.text_queue.get()
                text_input = dialogflow.types.TextInput(
                    text=text, language_code='en-US')

                query_input = dialogflow.types.QueryInput(text=text_input)

                response = session_client.detect_intent(
                    session=session, query_input=query_input)

                print('=' * 20)
                print('Query text: {}'.format(response.query_result.query_text))
                print('Detected intent: {} (confidence: {})\n'.format(
                    response.query_result.intent.display_name,
                    response.query_result.intent_detection_confidence))
                print('Fulfillment text: {}\n'.format(
                    response.query_result.fulfillment_text))

class TrelloThread(Thread):
    def __init__(self, text_queue):
        Thread.__init__(self)
        self.trello_queue = trello_queue
        self.shutdown_flag = Event()
    
    def run(self):
        while not self.shutdown_flag.is_set():
            if self.trello_queue.not_empty():
                continue
            

def main():
    # start main process
    # set logging
    logging.basicConfig(level=logging.ERROR)

    # handle ctrl-C
    signal.signal(signal.SIGINT, signal_handler)

    # start threads
    dialogflow_thread = DialogflowThread(text_queue)
    dialogflow_thread.start()


    huddle_thread = HuddleThread(text_queue)
    huddle_thread.start()


if __name__ == '__main__':
    main()
