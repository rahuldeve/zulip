from __future__ import absolute_import

from zerver.lib.outgoing_webhook import OutgoingWebhookBot, BotMessageActions

class GenericBot(OutgoingWebhookBot):

    def __init__(self, post_url, service_api_key, email, full_name):
        self.email = email
        self.full_name = full_name
        self.post_url = post_url
        self.service_api_key = service_api_key

    def process_command(self, command):
        return ('POST', '', {'command': command})

    def process_response(self, status_code, response_json, trigger_cache):
        return (BotMessageActions.succeed_with_message, response_json['message'])

    def handle_remote_failure(self, status_code, response_json, trigger_cache):
        return (BotMessageActions.fail_with_message, response_json['message'])
