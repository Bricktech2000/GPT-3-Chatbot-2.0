import discord
import openai
import asyncio
import sys
import re
import time
from conversation import Conversation

if len(sys.argv) != 4:
  print("Usage: python main.py <Discord bot token> <OpenAI API key> <OpenAI model name")
  exit(1)

# https://stackoverflow.com/questions/64221377/discord-py-rewrite-get-member-function-returning-none-for-all-users-except-bot
intents = discord.Intents.default()
intents.members = True
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
  async def do_react(message, arg): await message.add_reaction(arg)
  async def do_reply(message, arg): await message.reply(arg)

  async def do_sleep(message, arg):
    # https://stackoverflow.com/questions/49286640/how-to-set-bots-status
    # https://stackoverflow.com/questions/65773693/how-to-set-an-invisible-status-using-discord-py
    try:
      if arg.endswith('m'):
        time = int(arg[:-1]) * 60
      elif arg.endswith('h'):
        time = int(arg[:-1]) * 60 * 60
      else:
        time = 0
    except ValueError:
      time = 0

    await client.change_presence(status=discord.Status.offline)
    print('bot is sleeping')
    await asyncio.sleep(time)
    await client.change_presence(status=discord.Status.online)
    print('bot has woken')

  def do_log(text):
    async def func(message, arg):
      await message.channel.send(f'**COMMAND: {text}** {arg}')
    return func

  async def do_send(message, arg):
    async with message.channel.typing():
      typing_delay = len(arg) / TYPING_SPEED
      await asyncio.sleep(typing_delay)
    await message.channel.send(arg)

  async def do_nothing(message, arg):
    pass

  COMMAND_MAP = {
      'INIT': do_nothing,
      'SAVE': do_log('save last message'),
      'REACT': do_react,
      'REPLY': do_reply,
      'SLEEP': do_sleep,
      'SLEPT': do_nothing,
      'PHOTO': do_log('send photo:'),
      'VIDEO': do_log('send video:'),
      'MEME': do_log('send meme:'),
      'SEND': do_send
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


@client.event
async def on_ready():
  print(f"Logged in as {client.user}")


conversations = {}


@client.event
async def on_message(message):
  conversation_id = f'{message.channel.id}%{message.guild.id}'
  conversation = conversations.get(
      conversation_id, Conversation(CONVERSATION_TIMEOUT))

  # https://stackoverflow.com/questions/12597370/python-replace-string-pattern-with-output-of-function
  def replacer(match):
    return name_from_member(message.guild.get_member(int(match.group(1))))
  content = re.sub(r'<@(.+?)>', replacer, message.content.replace('\n', ' '))

  # TODO: media / pictures

  # TODO: timeout?

  if content != '':
    conversation = conversation.with_message(
        name_from_member(message.author), content, time.time())
  for attachment in message.attachments:
    conversation = conversation.with_message(
        name_from_member(message.author), 'PHOTO', time.time())
  conversations[conversation_id] = conversation

  prediction = GPT_3(
      conversation.get_conversation(NUM_MESSAGES) + '\n\n')

  if content.startswith('OVERRIDE '):
    prediction = f"{name_from_member(client.user)}: {content.replace('OVERRIDE ', '')}"

  print(conversation.get_conversation(NUM_MESSAGES) + '\n\n', end='')
  print(prediction, end='')
  print('\n\n')

  match = re.search(
      f"^(.+?): (({'|'.join(function_from_command()) }) )?(.*)$", prediction)
  if match:
    # prediction is correctly formed
    res_name, command, arg = match.group(1), \
        match.group(3) or 'SEND', match.group(4)

    if res_name == name_from_member(client.user):
      # GPT-3 predicts bot should take action
      await function_from_command(command)(message, arg)


openai.api_key = API_KEY
client.run(BOT_TOKEN)
