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
import picamera
import serial
from threading import Thread, Event
import threading
import snowboydecoder
import signal
import datetime
import time
import BlynkLib
from gpiozero import Button
from queue import Queue

import max30102
import aiy.assistant.auth_helpers
import aiy.voicehat
import aiy.audio
import aiy.assistant.grpc
from google.cloud import pubsub, vision

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)

SER_DEVICE = '/dev/ttyUSB0'
creds = aiy.assistant.auth_helpers.get_assistant_credentials()
model = "/home/pi/yogi/software/rpi/yogi.pmdl"
BLYNK_AUTH = 'b684cd44c4a641828f23679d8355a0c8'

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

def takephoto():
    camera = picamera.PiCamera()
    camera.capture('image.jpg')

def say_ip():
    ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
    aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'))

def power_off_pi():
    aiy.audio.say('Good bye!')
    subprocess.call('sudo shutdown -h now', shell=True)

def check_time(assistant_thread):
    while True:
        timenow = datetime.datetime.now().strftime("%H:%M")
        if timenow in assistant_thread._medicine_time:
            # assistant_thread.msg_queue.put(wave-hands)
            # play "medicine time!" sound track
            assistant_thread.msg_queue.put("wave")
            assistant_thread.textquery_flag.set()
            assistant_thread.textquery = "Medicine time"
            assistant_thread.medicine_flag.set()
            time.sleep(60)
        # sleep
        time.sleep(30)

def face_detect(vision_client, assistant_thread):
    # takephoto()
    with open('image.jpeg', 'rb') as image_file:
        content = image_file.read()
    face = vision_client.face_detection({'content': content}).face_annotations[0].landmarks[6].position
    assistant_thread.msg_queue.put("sr5 " + str(int(face.x)))
    assistant_thread.msg_queue.put("sr6 " + str(int(face.y)))


class VitalsThread(Thread):

    def __init__(self, assistant_thread):
        Thread.__init__(self)
        self.measuring_flag = Event()
        self.success_flag = Event()
        self.shutdown_flag = Event()
        self.interrupt = Button(26)
        self.hr = []
        self.spo2 = []
        self.temp = []
        self.validreads = 0
        self.assistant_thread = assistant_thread
        self.mx30 = max30102.MAX30102()

    def run(self):
        self.mx30.reset()
        self.mx30.initialize()
        for i in range(0, 100):
            self.interrupt.wait_for_press()
            self.mx30.read_sensor()
        self.mx30.HR_SpO2()
        while not self.shutdown_flag.is_set():
            self.assistant_thread.msg_queue.put("xo!")
            for i in range(0, 25):
                self.interrupt.wait_for_press()
                self.mx30.read_sensor()
            if self.mx30.spo2_valid() and self.mx30.hr_valid():
                self.assistant_thread.msg_queue.put("xt!")
                self.hr.append(self.mx30.HR)
                self.spo2.append(self.mx30.SpO2)
                self.temp.append(self.mx30.get_temperature())
                self.validreads+=1
                if self.validreads > 5:
                    self.assistant_thread.msg_queue.put("xr!")
                    average_hr = int(sum(self.hr)/5)
                    average_spo2 = int(sum(self.spo2)/5)
                    average_temp = int(sum(self.temp)/5)
                    self.assistant_thread.blynk.virtual_write(0, average_hr)
                    self.assistant_thread.blynk.virtual_write(1, average_spo2)
                    self.assistant_thread.blynk.virtual_write(2, average_temp)
                    self.assistant_thread.textquery = "Vitals {}, {}, {}".format(average_hr,
                        average_spo2, average_temp)
                    self.assistant_thread.textquery_flag.set()
                    self.hr = []
                    self.spo2 = []
                    self.temp = []
                    self.validreads = 0
            self.mx30.HR_SpO2()

class AssistantThread(Thread):
    """An assistant that runs in the background.

    The Google Assistant Library event loop blocks the running thread entirely.
    To support the button trigger, we need to run the event loop in a separate
    thread. Otherwise, the on_button_pressed() method will never get a chance to
    be invoked.
    """
    def __init__(self, msg_queue, blynk):
        Thread.__init__(self)
        self.snowboy = None
        self.textquery = None
        self.msg_queue = msg_queue
        self.blynk = blynk
        self._medicine_time = ["10:00", "14:00", "20:00"]
        self.shutdown_flag = Event()
        self.medicine_flag = Event()
        self.textquery_flag = Event()
        self.hotword_flag = Event()
        self.vision = vision.ImageAnnotatorClient(credentials=creds)

    def run(self):
        status_ui = aiy.voicehat.get_status_ui()
        status_ui.status('starting')
        assistant = aiy.assistant.grpc.get_assistant()
        button = aiy.voicehat.get_button()
        snowboy = snowboydecoder.HotwordDetector(model, sensitivity=0.5)
        follow_on = False
        with aiy.audio.get_recorder():
            while not self.shutdown_flag.is_set():
                status_ui.status('ready')
                self.msg_queue.put("xo!")
                if not self.textquery_flag.is_set():
                    if not follow_on:
                        print('Say yogi then speak')
                        snowboy.start(detected_callback=self.on_detect,
                               interrupt_check=self.hotword_flag.is_set,
                               sleep_time=0.03)
                        self.hotword_flag.clear()
                    status_ui.status('listening')
                    self.msg_queue.put("xl!")
                    print('Listening...')
                    req_text, resp_text, audio, follow_on = assistant.recognize()
                else:
                    req_text, resp_text, audio, follow_on = assistant.recognize(self.textquery)
                    self.textquery_flag.clear()
                    self.textquery = None
                if req_text:
                    self.blynk.virtual_write(3, 'User: "' + req_text + '" \n')
                    if req_text == 'shut down':
                        status_ui.status('stopping')
                        power_off_pi()
                        continue
                    if req_text == 'IP address':
                        say_ip()
                        continue
                elif self.medicine_flag.is_set():
                    self.msg_queue.put("pout")
                if resp_text:
                    self.blynk.virtual_write(3, 'Yogi: "' + resp_text + '" \n')
                if audio:
                    self.msg_queue.put("xr!")
                    self.msg_queue.put("fac 140")
                    aiy.audio.play_audio(audio)
                self.msg_queue.put("restore")
                self.medicine_flag.clear()

    def on_detect(self):
        face_detect_thread = Thread(target=face_detect, args=([self.vision, self]))
        face_detect_thread.start()
        self.msg_queue.put("xh!")
        self.hotword_flag.set()


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
    blynk = BlynkLib.Blynk(BLYNK_AUTH)
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGINT, signal_handler)

    assistant_thread = AssistantThread(msg_queue, blynk,)
    assistant_thread.start()

    # vitals_thread = VitalsThread(assistant_thread)
    # vitals_thread.start()

    subscription_thread = SubscriptionThread(msg_queue)
    subscription_thread.start()

    serial_thread = SerialThread(msg_queue)
    serial_thread.start()


    check_time_thread = Thread(target=check_time, args=([assistant_thread]))
    check_time_thread.start()

    blynk.run()

if __name__ == '__main__':
    main()
