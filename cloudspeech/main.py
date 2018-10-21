from __future__ import division

import re
import sys
import time
from threading import Thread

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import pyaudio
from six.moves import queue

# Imports the Google Cloud client library
from google.cloud import language
from google.cloud.language import enums as language_enums
from google.cloud.language import types as language_types

import trello
import vlc

# Instantiates a client
import dialogflow_v2 as dialogflow
session_client = dialogflow.SessionsClient()

session = session_client.session_path('project-huddle', '12')
print('Session path: {}\n'.format(session))

previous_final_transcript = ""
document = ""

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

running = True

class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk
        self._start_time = time.time()

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def reset(self):
        while True:
            try:
                self._buff.get(False)
            except queue.Empty:
                return

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)


def listen_print_loop(responses):
    """Iterates through server responses and prints them.

    The responses passed is a generator that will block until a response
    is provided by the server.

    Each response may contain multiple results, and each result may contain
    multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
    print only the transcription for the top alternative of the top result.

    In this case, responses are provided for interim results as well. If the
    response is an interim one, print a line feed at the end of it, to allow
    the next result to overwrite it, until the response is a final one. For the
    final one, print a newline to preserve the finalized transcription.
    """
    num_chars_printed = 0
    started = time.time()
    transcript = ""
    global previous_final_transcript 
    END_OF_SINGLE_UTTERANCE = types.StreamingRecognizeResponse.SpeechEventType.Value('END_OF_SINGLE_UTTERANCE')
    for response in responses:
        # print(response)
        if not response.results:
            continue

        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        result = response.results[0]
        if not result.alternatives:
            continue

        # Display the transcription of the top alternative.
        transcript = result.alternatives[0].transcript

        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        #
        # If the previous result was longer than this one, we need to print
        # some extra spaces to overwrite the previous result
        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + '\r')
            sys.stdout.flush()

            num_chars_printed = len(transcript)

        else:
            print(transcript + overwrite_chars)
            previous_final_transcript = transcript
            if "goodbye" in transcript:
                global running
                running = False
                break
            Thread(target=detect_intent_texts, args=([[transcript], 'en-US'])).start()
            break
        if response.speech_event_type == END_OF_SINGLE_UTTERANCE:
            break
    return 

def detect_intent_texts(texts, language_code):
    """Returns the result of detect intent with texts as inputs.

    Using the same `session_id` between requests allows continuation
    of the conversaion."""

    for text in texts:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)

        query_input = dialogflow.types.QueryInput(text=text_input)
        # print(query_input)
        response = session_client.detect_intent(
            session=session, query_input=query_input)

        intent = response.query_result.intent.display_name
        # print(response)
        print("Intent: " + intent)
        if intent == "Default Welcome Intent":
            print("Hello! I am Huddle, your team's virtual secretary. I'll be transcribing this meeting so talk away!")
            return
        elif intent == "Default Fallback Intent":
            return
        elif intent.startswith("discuss-task"):
            sub_intent = intent[14:]
            if sub_intent == "":
                return
            else:
                parameters = response.query_result.output_contexts[0].parameters
                # print(parameters)
                verb = parameters["verb"]
                terms = parameters["terms"]
                tools = parameters["tools"]
                proglang = parameters["proglang"]
                tools.extend(proglang)
                title_tools_proglang = ", ".join(tools)
                title_verb = ", ".join(verb)
                title_terms = ", ".join(terms)
                delimiter = ""
                if (len(tools) > 0 or len(proglang) > 0):
                    delimiter = ": "
                card_title = title_tools_proglang + delimiter + title_verb + " " + title_terms
                if (len(terms) > 0):
                    search = terms[0]
                elif (len(tools) > 0):
                    search = tools[0]
                elif (len(proglang) > 0):
                    search = proglang[0]
                else:
                    search = verb[0]
                print(card_title)
                if (sub_intent == "to-do" or sub_intent == "doing" or sub_intent == "done"):
                    destination = sub_intent
                    Thread(target=trello.find_card, args=([search, card_title, destination, "", ""])).start()
                    return
                elif (sub_intent == "add-member"):
                    name = parameters["name"]
                    print(card_title)
                    Thread(target=trello.find_card, args=([search, card_title, "", "", name])).start()
                    return
                elif (sub_intent == "add-duedate"):
                    date = parameters["date"]
                    # print(card_title)
                    Thread(target=trello.find_card, args=([search, card_title, "", date, ""])).start()
                    return
                else:
                    return
        else:
            parameters = response.query_result.parameters
            # print(parameters)
            verb = parameters["verb"]
            terms = parameters["terms"]
            tools = parameters["tools"]
            proglang = parameters["proglang"]
            if (len(terms) > 0):
                search = terms[0]
            elif (len(tools) > 0):
                search = tools[0]
            elif (len(proglang) > 0):
                search = proglang[0]
            else:
                search = verb[0]
            tools.extend(proglang)
            title_tools_proglang = ", ".join(tools)
            title_verb = ", ".join(verb)
            title_terms = ", ".join(terms)
            delimiter = ""
            if (len(tools) > 0 or len(proglang) > 0):
                delimiter = ": "
            card_title = title_tools_proglang + delimiter + title_verb + " " + title_terms
            destination = intent
            # print(card_title)
            Thread(target=trello.find_card, args=([search, card_title, destination, "", ""])).start()
            return
        

def main():
    global running
    # p = vlc.MediaPlayer("./output.mp3")
    # p.play()
    # time.sleep(7)
    # See http://g.co/cloud/speech/docs/languages
    # for a list of supported languages.
    language_code = 'en-US'  # a BCP-47 language tag

    client = speech.SpeechClient()
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code)
    streaming_config = types.StreamingRecognitionConfig(
        config=config,
        single_utterance=True,
        interim_results=True)

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        while running:
            stream.reset()
            audio_generator = stream.generator()
            requests = (types.StreamingRecognizeRequest(audio_content=content)
                        for content in audio_generator)
            responses = client.streaming_recognize(streaming_config, requests)

            # Now, put the transcription responses to use.
            listen_print_loop(responses)


if __name__ == '__main__':
    main()