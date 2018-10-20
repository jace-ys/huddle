#!/usr/bin/env python3

import logging
import sys
import json
import subprocess
import serial
from threading import Thread, Event
import threading
import signal
import datetime
import time
from gpiozero import Button
from queue import Queue

import aiy.voicehat
import aiy.audio
import aiy.assistant.grpc

logging.basicConfig(
    level=logging.WARNING,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)

# initialise instances of app objects
msg_queue = Queue()


def signal_handler(signal, frame):
    """ Ctrl+C handler to cleanup """
    for t in threading.enumerate():
        print(t)
        if t.name != 'MainThread':
            t.shutdown_flag.set()

    print('Goodbye!')
    sys.exit(1)

def contains_word(string, word):
    return (' ' + word + ' ') in (' ' + string + ' ')

def say_ip():
    ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
    aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'))

def power_off_pi():
    aiy.audio.say('Good bye!')
    subprocess.call('sudo shutdown -h now', shell=True)

class HuddleThread(Thread):

    def __init__(self, msg_queue):
        Thread.__init__(self)
        self.textquery = None
        self.msg_queue = msg_queue
        self.shutdown_flag = Event()
        self.textquery_flag = Event()

    def run(self):
        assistant = aiy.assistant.grpc.get_assistant()
        button = aiy.voicehat.get_button()
        first_run = True
        time.sleep(3)
        self.textquery = "Talk to Huddle"
        with aiy.audio.get_recorder():
            while not self.shutdown_flag.is_set():
                print("Ready")
                if self.textquery:
                    req_text, resp_text, audio, follow_on = assistant.recognize(self.textquery)
                    self.textquery = None
                else:
                    if first_run:
                        button.wait_for_press()
                        first_run = False
                    print("Listening")
                    req_text, resp_text, audio, follow_on = assistant.recognize()
                if req_text:
                    print("Team: " + req_text)
                if resp_text:
                    print("Huddle: " + resp_text)
                    if req_text == 'shut down':
                        power_off_pi()
                        continue
                    if req_text == 'IP address':
                        say_ip()
                        follow_on = False
                        continue
                if audio:
                    aiy.audio.play_audio(audio)
                self.textquery_flag.clear()


def main():
    # start main process
    # kill video streams
    subprocess.call('sudo pkill uv4l', shell=True)

    # set logging
    logging.basicConfig(level=logging.ERROR)

    # handle ctrl-C
    signal.signal(signal.SIGINT, signal_handler)

    # start threads
    huddle_thread = HuddleThread(msg_queue)
    huddle_thread.start()

if __name__ == '__main__':
    main()
