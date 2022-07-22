# https://stackoverflow.com/questions/3768895/how-to-make-a-class-json-serializable
import json


class Conversation(dict):
  def __init__(self, conversation_timeout, messages=None, last_message_timestamp=0):
    self.conversation_timeout = conversation_timeout
    self.messages = messages if messages is not None else []
    self.last_message_timestamp = last_message_timestamp
    super().__init__(self.__dict__)

  def with_message(self, name, content, timestamp):
    is_conversation_timed_out = self.last_message_timestamp + \
        self.conversation_timeout < timestamp
    init_message = [f'{name}: INIT;'] if is_conversation_timed_out else []
    new_message = [f'{name}: {content}'] if content else []

    return Conversation(self.conversation_timeout, self.messages + init_message + new_message, timestamp)

  def without_last(self):
    return Conversation(self.conversation_timeout, self.messages[:-1], self.last_message_timestamp)

  def get_last_messages(self, length):
    return '\n'.join(self.messages[-length:])


class ConversationManager(dict):
  def __init__(self, conversation_timeout, serialize_path):
    self.conversations = {}
    self.conversation_timeout = conversation_timeout
    self.serialize_path = serialize_path

    try:
      with open(self.serialize_path, 'r') as f:
        self.__dict__ = json.load(f)
        self.serialize_path = serialize_path  # do not serialize
        self.conversations = {k: Conversation(**v) for k, v in
                              self.conversations.items()}  # rebuild conversations
    except FileNotFoundError:
      print('Notice: No serialized conversations found.')

    super().__init__(self.__dict__)

  def get(self, *ids):
    conversation_id = '\n'.join(map(str, ids))  # make hashable

    if conversation_id not in self.conversations:
      self.conversations[conversation_id] = Conversation(
          self.conversation_timeout)

    def save(conversation):
      self.conversations[conversation_id] = conversation
      with open(self.serialize_path, 'w') as f:
        json.dump(self, f)

    return self.conversations[conversation_id], save

  def get_all_ids(self):
    return list(map(lambda key: key.split('\n'), self.conversations.keys()))
