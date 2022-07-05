import math
import discord
import openai
import asyncio
import sys
import re
import time
import random
from conversation import Conversation
from conversation import ConversationManager

if len(sys.argv) != 4:
  print("Usage: python main.py <Discord bot token> <OpenAI API key> <OpenAI model name")
  exit(1)

# https://stackoverflow.com/questions/64221377/discord-py-rewrite-get-member-function-returning-none-for-all-users-except-bot
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.reactions = True
client = discord.Client(intents=intents)

BOT_TOKEN = sys.argv[1]
API_KEY = sys.argv[2]
ENGINE = sys.argv[3]

NUM_MESSAGES = 8  # the number of messages to append to the training data
TEMPERATURE = 0.8  # the "originality" of GPT-3's answers
MAX_TOKENS = 50  # the maximal length of GPt-3's answers
TYPING_SPEED = 15  # characters per second
CONVERSATION_TIMEOUT = 120  # seconds, time for a conversation to be considered dead


def name_from_member(member):
  # TODO: move out of this file
  NAME_MAP = {
      296473451190026240: 'max',
      362627068430909450: 'emilien',
      349323309357465619: 'alex',
      423516682548412418: 'reid',
      381859631481487361: 'amelie',
      334409678387806208: 'cameron',
      426167359665995777: 'edouard',
      529778786330345483: 'jaya',
      858772258394996768: 'kiera',
      573621663753568306: 'courtney',
      0: 'grace'
  }
  id = member.id if member.id != client.user.id else 0
  return NAME_MAP.get(id, member.display_name).lower()


def function_from_command(command=None):
  async def do_react(message, conversation, save, arg):
    save(conversation)
    await message.add_reaction(arg)

  async def do_reply(message, conversation, save, arg):
    save(conversation)
    await message.reply(arg)

  async def do_sleep(message, conversation, save, arg):
    # https://stackoverflow.com/questions/49286640/how-to-set-bots-status
    # https://stackoverflow.com/questions/65773693/how-to-set-an-invisible-status-using-discord-py

    min, max = 30, 1 * 60 * 60  # 5 seconds to 3 hours
    # make it more likely to sleep for less time
    n = 10
    delay = math.pow(random.uniform(math.pow(min, 1/n), math.pow(max, 1/n)), n)

    print(f'bot is sleeping for {round(delay)}s\n\n')
    await client.change_presence(status=discord.Status.offline)
    await asyncio.sleep(delay)
    await client.change_presence(status=discord.Status.online)
    print(f'bot is awake\n\n')

    conversation = conversation.without_last().with_message(
        name_from_member(client.user), '', time.time())

    save(conversation)
    await execute(message, conversation, save)

  def do_log(text):
    async def func(message, conversation, save, arg):
      await message.channel.send(f'**COMMAND: {text}** {arg}')
    return func

  async def do_send(message, conversation, save, arg):
    save(conversation)
    async with message.channel.typing():
      typing_delay = len(arg) / TYPING_SPEED
      await asyncio.sleep(typing_delay)
    await message.channel.send(arg)

  async def do_nothing(message, conversation, save, arg):
    pass

  COMMAND_MAP = {
      'INIT;': do_sleep,
      'SAVE;': do_log('save last message'),
      'REACT: ': do_react,
      'REPLY: ': do_reply,
      'PHOTO: ': do_log('send photo:'),
      'VIDEO: ': do_log('send video:'),
      'PHOTO;': do_log('send random photo'),
      'VIDEO;': do_log('send random video'),
      'MEME: ': do_log('send meme:'),
      'SCREEN: ': do_log('send screenshot:'),
      '': do_send
  }

  return COMMAND_MAP[command] if command is not None else COMMAND_MAP


def GPT_3(messages):
  response_object = openai.Completion.create(
      engine=ENGINE,
      prompt=messages,
      temperature=TEMPERATURE,
      max_tokens=MAX_TOKENS,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0.6,
      stop=["\n"],
  )

  # remove whitespace recommended by OpenAI
  return str(response_object['choices'][0]['text'])[1:]


@ client.event
async def on_ready():
  print(f"Logged in as {client.user}")


conversation_manager = ConversationManager(CONVERSATION_TIMEOUT)


@ client.event
async def on_reaction_add(reaction, user):
  message = reaction.message
  conversation, save = conversation_manager.get(
      message.channel.id, message.guild.id)

  if user.id != client.user.id:
    conversation = conversation.with_message(
        name_from_member(user), f'REACT: {reaction.emoji}', time.time())

  save(conversation)

  await execute(reaction.message, conversation, save)


@ client.event
async def on_message(message):
  conversation, save = conversation_manager.get(
      message.channel.id, message.guild.id)

  # https://stackoverflow.com/questions/12597370/python-replace-string-pattern-with-output-of-function
  def replacer(match):
    return name_from_member(message.guild.get_member(int(match.group(1))))
  content = re.sub(r'<@(.+?)>', replacer, message.content.replace('\n', ' '))

  if message.author.id != client.user.id and content != '':
    conversation = conversation.with_message(
        name_from_member(message.author), content, time.time())
  for attachment in message.attachments:
    conversation = conversation.with_message(
        name_from_member(message.author), 'PHOTO;', time.time())

  save(conversation)

  await execute(message, conversation, save)


async def execute(message, conversation, save):
  # TODO: media / pictures

  # TODO: auto wake after inactivity and sleeping

  if message.guild.get_member(client.user.id).status != discord.Status.online:
    # return if the bot is sleeping
    return

  prediction = GPT_3(
      conversation.get_last_messages(NUM_MESSAGES) + '\n\n')

  if message.content.startswith('OVERRIDE: '):
    prediction = f"{name_from_member(client.user)}: {message.content.replace('OVERRIDE: ', '')}"

  print(conversation.get_last_messages(NUM_MESSAGES) + '\n\n', end='')
  print(prediction, end='')
  print('\n\n')

  match = re.search(
      f"^(.+?): ({'|'.join(function_from_command())})(.*?)$", prediction)
  if match:
    # prediction is correctly formed
    res_name, command, arg = match.group(1), \
        match.group(2), match.group(3)

    if res_name == name_from_member(client.user) or command == 'INIT;':
      # GPT-3 predicts bot should take action
      conversation, save = conversation_manager.get(
          message.channel.id, message.guild.id)

      conversation = conversation.with_message(
          name_from_member(client.user), f'{command}{arg}', time.time())

      await function_from_command(command)(message, conversation, save, arg)


openai.api_key = API_KEY
client.run(BOT_TOKEN)
