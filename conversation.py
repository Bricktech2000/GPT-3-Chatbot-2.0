import time


class Conversation:
  def __init__(self, conversation_timeout, channel, messages=[], last_message_timestamp=0):
    self.conversation_timeout = conversation_timeout
    self.channel = channel
    self.messages = messages
    self.last_messsage_timestamp = last_message_timestamp

  def with_message(self, name, content, timestamp):
    is_conversation_timed_out = self.last_messsage_timestamp + \
        self.conversation_timeout < timestamp
    init_message = [f'{name}: INIT'] if is_conversation_timed_out else []
    new_message = [f'{name}: {content}']

    return Conversation(self.conversation_timeout, self.channel, self.messages + init_message + new_message, timestamp)

  def get_conversation(self, length):
    return '\n'.join(self.messages[-length:])
