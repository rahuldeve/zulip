from __future__ import absolute_import

import json
import re
from zerver.lib.outgoing_webhook import OutgoingWebhookBotInterface, BotMessageActions

class IsItUpBot(OutgoingWebhookBotInterface):
    email = "isitup-bot@zulip.com"
    full_name = "IsItUpBot"

    def __init__(self, post_url, service_api_key, email=None, full_name=None):
        self.post_url = post_url
        self.service_api_key = service_api_key

    def process_command(self, command):
        tokens = command.lower().split(' ')
        url = None
        for token in tokens:
            if re.search(u'\..+', token):
                url = token

        # This map will be unpacked directly onto do_rest_call function. Hence the
        # existance of the following keywords is a must.
        # The 'trigger_cache' key is present for the sake of convienence. Its
        # value will be passed onto the other functions and can be used to pass
        # values between them. Please use this map instead of creating local
        # variables to keep the bot interface stateless. If you do not wish to
        # utilise it just pass an empty map.
        processed_command = {'http_operation': 'GET',
                             'relative_url_path': url + '.json',
                             'kwargs': {},
                             'trigger_cache': {}
                            }

        return processed_command

    def process_response(self, status_code, response_json, trigger_cache):
        status = int(response_json['status_code'])
        if status == 1:
            response = '**' + response_json['domain'] + '** is **up**!'
            return (BotMessageActions.succeed_with_message, response)
        else:
            response = '**' + response_json['domain'] + '** is ***down!**\n' + \
                    '`\n' + json.dumps(response_json, indent=4) + '\n`'
            return (BotMessageActions.succeed_with_message, response)

    def handle_remote_failure(self, status_code, response_json, trigger_cache):
        return (BotMessageActions.fail_with_message, '**Failed: **' + response_json)

    def handle_invalid_command(self, command):
        return (BotMessageActions.fail_with_message, '**Invalid command: **' + command)
