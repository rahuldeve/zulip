from __future__ import absolute_import
from typing import Any, Iterable, Dict, Optional, Set, Tuple, Type, Callable
from six import text_type

import requests
import sys
import inspect
import logging
from six.moves import urllib, reduce

from zerver.models import get_outgoing_webhook_bot_profile, Realm
from zerver.lib.actions import internal_send_message
from zerver.lib.queue import queue_json_publish

class OutgoingWebhookBotInterface(object):
    email = None # type: text_type
    full_name = None # type: text_type

    def __init__(self, post_url, service_api_key):
        self.post_url = None # type: text_type
        self.service_api_key = None # type: text_type

    def process_command(self, command):
        raise NotImplementedError()

    def process_response(self, status_code, response_json, trigger_cache):
        raise NotImplementedError()

    def handle_remote_failure(self, status_code, response_json, trigger_cache):
        raise NotImplementedError()

class OutgoingWebhookBot(object):
    email = None # type: text_type
    full_name = None # type: text_type

    def __init__(self):
        self.post_url = None # type: text_type
        self.service_api_key = None # type: text_type

    def process_command(self, command):
        raise NotImplementedError()

    def process_response(self, status_code, response_json, trigger_cache):
        raise NotImplementedError()

    def handle_remote_failure(self, status_code, response_json, trigger_cache):
        raise NotImplementedError()

    def handle_invalid_command(self, command):
        raise NotImplementedError()

    def do_rest_call(self, http_operation, relative_url_path, kwargs, trigger_cache, timeout=None):
        # type: (str, str, Dict[str, Any], Dict[str, Any], float) -> Tuple[Callable[[Any, Any], Any], text_type]
        final_url = urllib.parse.urljoin(self.post_url, relative_url_path)

        kwargs['timeout'] = timeout

        try:
            response = requests.request(http_operation, final_url, **kwargs)
            if str(response.status_code).startswith('2'):
                return self.process_response(response.status_code, response.json(), trigger_cache)

            # On 50x errors, try retry
            elif str(response.status_code).startswith('5'):
                return (BotMessageActions.request_retry, 'Maximum retries exceeded')
            else:
                return self.handle_remote_failure(response.status_code, response.json(), trigger_cache)

        except requests.exceptions.Timeout:
            logging.info("Trigger event on %s timed out. Retrying" % (self.full_name))
            return (BotMessageActions.request_retry, 'Maximum retries exceeded')

        except requests.exceptions.RequestException as e:
            response_message = "An exception occured! See the logs for more information."
            logging.exception("Outhook trigger failed:\n %s" % (e,))
            return (BotMessageActions.fail_with_message, response_message)

class BotMessageActions():

    @staticmethod
    def send_response_message(bot_email, trigger_message, response_message_content):
        recipient_type_name = trigger_message['type']
        if recipient_type_name == 'stream':
            recipients = trigger_message['display_recipient']
            internal_send_message(bot_email, recipient_type_name, recipients,
                                  trigger_message['subject'], response_message_content)
        else:
            # Private message; only send if the bot is there in the recipients
            trigger_message_recipients = [recipient['email'] for recipient in trigger_message['display_recipient']]
            if bot_email in trigger_message_recipients:
                recipients = ','.join(trigger_message_recipients)
                internal_send_message(bot_email, recipient_type_name, recipients,
                              trigger_message['subject'], response_message_content)

    @classmethod
    def succeed_with_message(cls, event, success_message):
        bot_email = event['bot_email']
        trigger_message = event['message']
        cls.send_response_message(bot_email, trigger_message, success_message)

    @classmethod
    def fail_with_message(cls, event, failure_message):
        bot_email = event['bot_email']
        trigger_message = event['message']
        cls.send_response_message(bot_email, trigger_message, failure_message)

    @classmethod
    def request_retry(cls, event, failure_message):
        event['retry'] += 1
        if event['retry'] > 3:
            bot_email = event['bot_email']
            command = event['command']
            cls.fail_with_message(event, failure_message)
            logging.warning("Maximum retries exceeded for trigger:%s event:%s" % (bot_email, command))
        else:
            queue_json_publish("outhook_worker", event, lambda x: None)

def load_available_bots():
    # type: () -> Dict[text_type, type]
    modules = load("zerver.outgoing_webhooks")
    class_members = [inspect.getmembers(module, inspect.isclass) for module in modules] # type: List[List[Tuple[str, Any]]]
    if len(class_members) > 0:
        class_member_list = reduce(list.__add__, class_members) # type: List[Tuple[str, Any]]
    else:
        class_member_list = []

    bot_classes = {cls.email:cls for cls_name,cls in class_member_list if issubclass(cls, OutgoingWebhookBotInterface) and cls.email is not None}
    return bot_classes

def create_bot_instance(bot_interface):
    # type: (Any) -> Any
    return type(bot_interface.full_name + 'Handler', (bot_interface, OutgoingWebhookBot), {})

def get_outgoing_webhook_bot_handler(bot_email, realm):
    # type: (text_type, Realm) -> Any
    bot_profile = get_outgoing_webhook_bot_profile(bot_email, realm)
    bot_interface = available_outhook_bots[bot_email]
    bot_instance = create_bot_instance(bot_interface)(post_url=bot_profile.post_url,
                                                      service_api_key=bot_profile.service_api_key)
    return bot_instance

available_outhook_bots = load_available_bots()
