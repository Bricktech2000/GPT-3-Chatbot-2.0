class Conversation:
  def __init__(self, conversation_timeout, messages=[], last_message_timestamp=0):
    self.conversation_timeout = conversation_timeout
    self.messages = messages
    self.last_message_timestamp = last_message_timestamp

  def with_message(self, name, content, timestamp):
    is_conversation_timed_out = self.last_message_timestamp + \
        self.conversation_timeout < timestamp
    init_message = [f'{name}: INIT'] if is_conversation_timed_out else []
    new_message = [f'{name}: {content}'] if content else []

    return Conversation(self.conversation_timeout, self.messages + init_message + new_message, timestamp)

  def without_last(self):
    return Conversation(self.conversation_timeout, self.messages[:-1], self.last_message_timestamp)

  def get_last_messages(self, length):
    return '\n'.join(self.messages[-length:])


class ConversationManager:
  def __init__(self, conversation_timeout):
    self.conversations = {}
    self.conversation_timeout = conversation_timeout

  def get(self, *ids):
    conversation_id = '\n'.join(map(str, ids))

    if conversation_id not in self.conversations:
      self.conversations[conversation_id] = Conversation(
          self.conversation_timeout)

    def save(conversation):
      self.conversations[conversation_id] = conversation

    return self.conversations[conversation_id], save

  def get_all_ids(self):
    return list(map(lambda key: key.split('\n'), self.conversations.keys()))
