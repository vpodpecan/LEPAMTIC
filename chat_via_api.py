import os
import sys
import pathlib
import logging
import pickle
import argparse
import time
import json
import base64
import mimetypes
import logging

from openai import OpenAI

logger = logging.getLogger(f"lepamtic.{__name__}")


def image_to_base64(image_path):
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith('image'):
        raise ValueError('Not an image')
    with open(image_path, 'rb') as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    image_base64 = f"data:{mime_type};base64,{encoded_string}"
    return image_base64


class ChatDialog:
    def __init__(self, 
                 api_key,
                 organization=None,
                 model='gpt-4o', 
                 base_url='https://api.openai.com/v1',
                 role='You act as a helpful assistant.',
                 as_json=False,
                 call_wait_time=0.05,
                 reset_for_each_call=False):
        self.base_url = base_url
        self.organization = organization
        self.api_key = api_key
        self.model = model
        self.role = role
        self.as_json = as_json
        if self.as_json:
            self.role += ' ' + 'Always respond exclusively in valid, RFC 8259-compliant JSON format.'

        self.reset_for_each_call = reset_for_each_call
        self.last_api_event_timestamp = None
        self.call_wait_time = call_wait_time

        self.messages = []
        if self.role:
            self.messages.append({"role": "system", "content": self.role})
        self.client = self.create_client()

    def create_client(self):
        return OpenAI(api_key=self.api_key,
                      base_url=self.base_url,
                      organization=self.organization)
    
    @classmethod
    def load(klas, pickle_file):
        with open(pickle_file, 'rb') as fp:
            instance = pickle.load(fp)
        instance.client = instance.create_client()  # it was removed before dumping
        return instance

    def save(self, pickle_file):
        self.client = None  # this will avoid pickling _thread.RLock' object
        with open(pickle_file, 'wb') as fp:
            pickle.dump(self, fp)
        self.client = self.create_client()

    def enforce_limits(self):
        if not self.last_api_event_timestamp:
            return
        else:
            while (time.time() - self.last_api_event_timestamp) < self.call_wait_time:
                time.sleep(0.5)

    def analyze_image(self, impath, prompt, model='gpt-4-vision-preview', max_tokens=300):
        imgb64 = image_to_base64(impath)
        if self.as_json:
            messages = [{"role": "system", "content": self.role}]
        else:
            messages = []
        #     prompt = prompt + '\n' + 'You must return a RFC8259 compliant JSON, markdown output is prohibited.'
        messages.append({"role": "user",
                         "content": [
                             {"type": "text", 
                              "text": prompt},
                             {"type": "image_url",
                              "image_url": {
                                  "url": imgb64,
                                  "detail": "low"}
                             }
                         ]
                        })
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        
        result = response.choices[0].message.content
        return json.loads(result) if self.as_json else result

    
    def ask(self, question, print_answer=False, **kwargs):
        self.enforce_limits()            
        if self.reset_for_each_call:
            self.reset()
            
        self.messages.append({"role": "user", "content": question})
        if self.as_json:
            kwargs['response_format']= {"type": "json_object"}

        # quick hacks
        if 'googleapis' in self.base_url and 'seed' in kwargs:
            del kwargs['seed']
        if 'openai' in self.base_url and 'temperature' in kwargs and (self.model.startswith('o1') or self.model.startswith('o3') or self.model.startswith('o4') or self.model.startswith('gpt-5')):
            del kwargs['temperature']
        if 'openai' in self.base_url and 'reasoning_effort' in kwargs and not (self.model.startswith('o1') or self.model.startswith('o3') or self.model.startswith('o4') or self.model.startswith('gpt-5')):
            del kwargs['reasoning_effort']
        if 'openai' in self.base_url and 'verbosity' in kwargs and not self.model.startswith('gpt-5'):
            del kwargs['verbosity']

        logger.debug(f'API call: model: {self.model}, kwargs: {kwargs}')

        response = self.client.chat.completions.create(model=self.model,
                                                       messages=self.messages,
                                                       **kwargs)
        self.last_api_event_timestamp = time.time()
        
        answer = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": answer})
        if self.as_json:
            answer = json.loads(answer)
        # self.messages.append({"role": "assistant", "content": answer})  ce je tu llama.cpp ne dela...?
        if print_answer:
            print(answer)
        return answer

    def get_last_answer(self):
        for message in self.messages[::-1]:
            if message['role'] == 'assistant':
                return message['content']
        raise ValueError('No answers found')
    
    def reset(self):
        self.messages = []
        if self.role:
            self.messages.append({"role": "system", "content": self.role})

    def forced_dialog(self, questions, **kwargs): #, print_intermediate_answers=False, print_final_answer=True):
        '''Here we ask a series of questions and not show the answers except the last one.
        The idea is that we have prepared a dialog that we know will give us desired results in the end.
        ''' 
        if self.reset_for_each_call:
            raise ValueError('Please set reset_for_each_call to False!')
            
        self.reset()
        for q in questions:
            if (isinstance(q, tuple) or isinstance(q, list)) and callable(q[0]):  # function to call which does something with the last result
                function = q[0]
                args = q[1:]
                text = self.messages[-1]['content']
                function(text, *args)
            elif isinstance(q, str):
                self.ask(q, print_answer=False, **kwargs)
            else:
                print(f'Ignoring invalid entry "{repr(q)}"')
    
    def print_context(self, filename=None):
        lines = []
        for i, message in enumerate(self.messages):
            if message['role'] == 'assistant':
                prefix = 'ANSWER'
            elif message['role'] == 'user':
                prefix = 'QUESTION'
            elif message['role'] == 'system':
                prefix = 'SYSTEM'
            else:
                prefix = '?'
            lines.append(f'{prefix}: {message["content"]}')
        if filename is not None:
            with open(filename, 'w') as fp:
                fp.write('\n'.join(lines))
        else:
            print('\n'.join(lines))
