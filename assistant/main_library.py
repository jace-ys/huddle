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

"""Run a recognizer using the Google Assistant Library with button support.

The Google Assistant Library has direct access to the audio API, so this Python
code doesn't need to record audio. Hot word detection "OK, Google" is supported.

The Google Assistant Library can be installed with:
    env/bin/pip install google-assistant-library==0.0.2

It is available for Raspberry Pi 2/3 only; Pi Zero is not supported.
"""

import logging
import sys
import json
import subprocess
import serial
from threading import Thread, Event
import threading
import snowboythreaded
import signal
import datetime
import time
from queue import Queue

import aiy.assistant.auth_helpers
import aiy.voicehat
import aiy.audio
from google.assistant.library import Assistant
from google.assistant.library.event import EventType
from google.cloud import pubsub

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)

SER_DEVICE = '/dev/ttyUSB0'
creds = aiy.assistant.auth_helpers.get_assistant_credentials()
model = "/home/pi/yogi/software/rpi/yogi.pmdl"

face_command_map = {
    'happy': 'fac 10',
    'very happy': 'fac 20',
    'sad': 'fac 30',
    'very sad': 'fac 40',
    'tongue': 'fac 50',
    'dead': 'fac 60',
    'scared': 'fac 70',
    'sleeping': 'fac 80',
    'confused': 'fac 90',
    'bored': 'fac 100',
    'love': 'fac 110',
    'disgusted': 'fac 120',
    'angry': 'fac 130',
    'speaking': 'fac 140',
}


def signal_handler(signal, frame):
    """ Ctrl+C handler to cleanup """
    for t in threading.enumerate():
        print(t)
        if t.name != 'MainThread':
            t.shutdown_flag.set()

    print('Goodbye!')
    sys.exit(1)


def say_ip():
    ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
    aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'))


def check_time(assistant_thread):
    while True:
        timenow = datetime.datetime.now().strftime("%H:%M")
        if timenow in assistant_thread._medicine_time:
            # assistant_thread.msg_queue.put(wave-hands)
            # play "medicine time!" sound track
            assistant_thread.put("wave")
            assistant_thread.medicine_flag.set()
            time.sleep(60)
        # sleep
        time.sleep(30)


class AssistantThread(Thread):
    """An assistant that runs in the background.

    The Google Assistant Library event loop blocks the running thread entirely.
    To support the button trigger, we need to run the event loop in a separate
    thread. Otherwise, the on_button_pressed() method will never get a chance to
    be invoked.
    """
    def __init__(self, msg_queue):
        Thread.__init__(self)
        self._can_start_conversation = False
        self._assistant = None
        self._snowboy = None
        self.msg_queue = msg_queue
        self._medicine_time = ["10:00", "14:00", "20:00"]
        self.shutdown_flag = Event()
        self.medicine_flag = Event()

    def run(self):
        with Assistant(creds, "Meep") as assistant:
            self._assistant = assistant
            while not self.shutdown_flag.is_set():
                for event in assistant.start():
                    self._process_event(event)

    def _process_event(self, event):
        status_ui = aiy.voicehat.get_status_ui()
        if event.type == EventType.ON_START_FINISHED:
            status_ui.status('ready')
            self._can_start_conversation = True
            #Start the voicehat button trigger
            #aiy.voicehat.get_button().on_press(self._on_detect)
            self._snowboy = snowboythreaded.ThreadedDetector(self._on_detect, model, sensitivity=0.5)
            self._snowboy.start()
            self._snowboy.start_recog(sleep_time=0.03)
            if sys.stdout.isatty():
                print('Say "Yogi", then speak. '
                      'Press Ctrl+C to quit...')

        elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
            self._can_start_conversation = False
            status_ui.status('listening')
            self.msg_queue.put("xl!")

        elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED:
            print('You said: ', event.args['text'])
            if event.args['text'].lower() == 'ip address':
                self._assistant.stop_conversation()
                say_ip()

        elif event.type == EventType.ON_END_OF_UTTERANCE:
            status_ui.status('thinking')
            self.msg_queue.put("xt!")

        elif event.type == EventType.ON_RESPONDING_STARTED:
            self.msg_queue.put("xr!")
            self.msg_queue.put("fac 140")

        elif event.type == EventType.ON_RESPONDING_FINISHED:
            self.msg_queue.put("restore")

        elif event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT:
            status_ui.status('ready')
            self.msg_queue.put("xo!")
            if self.medicine_flag.is_set():
                self.msg_queue.put("pout")
            self._can_start_conversation = True

        elif event.type == EventType.ON_CONVERSATION_TURN_FINISHED:
            status_ui.status('ready')
            self.msg_queue.put("xo!")
            self._can_start_conversation = True

        elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
            sys.exit(1)

    def _on_detect(self):
        # Check if we can start a conversation. 'self._can_start_conversation'
        # is False when either:
        # 1. The assistant library is not yet ready; OR
        # 2. The assistant library is already in a conversation.
        if self._can_start_conversation:
            self.msg_queue.put("xh!")
            self._assistant.start_conversation()


class SubscriptionThread(Thread):

    def __init__(self, msg_queue):
        Thread.__init__(self)
        self.shutdown_flag = Event()
        self.msg_queue = msg_queue

        # Create a new pull subscription on the given topic
        subscriber = pubsub.SubscriberClient(credentials=creds)
        topic_name = 'projects/fiery-celerity-194216/topics/YogiMessages'
        sub_name = 'projects/fiery-celerity-194216/subscriptions/PythonYogiSub'
        self.subscription = subscriber.subscribe(sub_name)

    def process_messages(self, message):
        json_string = str(message.data)[3:-2]
        json_string = json_string.replace('\\\\', '')
        # create dict from json string
        try:
            json_obj = json.loads(json_string)
        except Exception as e:
            logging.error('JSON Error: %s', e)
        command = json_obj['command']
        print('pub/sub: ' + command)

        if command == 'face':
            value = json_obj['value']
            self.msg_queue.put(face_command_map[value])
        message.ack()

    def run(self):
        """ Poll for new messages from the pull subscription """
        future = self.subscription.open(self.process_messages)
        try:
          future.result()
        except Exception as ex:
            self.subscription.close()
            raise


class SerialThread(Thread):

    def __init__(self, msg_queue):
        Thread.__init__(self)
        self.shutdown_flag = Event()
        self.msg_queue = msg_queue
        self.serial = serial.Serial(SER_DEVICE, 9600)

    def run(self):
        while not self.shutdown_flag.is_set():
            if not self.msg_queue.empty():
                cmd = self.msg_queue.get()
                self.serial.write(str.encode(cmd))
                print('Serial sending ' + cmd)


def main():
    msg_queue = Queue()
    signal.signal(signal.SIGINT, signal_handler)

    assistant_thread = AssistantThread(msg_queue)
    assistant_thread.start()

    subscription_thread = SubscriptionThread(msg_queue)
    subscription_thread.start()

    serial_thread = SerialThread(msg_queue)
    serial_thread.start()


    check_time_thread = Thread(target=check_time, args=([assistant_thread]))
    check_time_thread.start()

if __name__ == '__main__':
    main()
