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


async def do_react(message, arg): await message.add_reaction(arg)
async def do_reply(message, arg): await message.reply(arg)


async def do_sleep(message, arg):
  # https://stackoverflow.com/questions/49286640/how-to-set-bots-status
  try:
    if arg.endswith('m'):
      time = int(arg[:-1]) * 60
    elif arg.endswith('h'):
      time = int(arg[:-1]) * 60 * 60
    else:
      time = 0
  except ValueError:
    time = 0

  client.bot.set_status('invisible')
  await asyncio.sleep(time)
  message.channel.send('')
  client.bot.set_status('available')


def do_send(text):
  async def func(message, arg):
    await message.channel.send(f'**COMMAND: {text}** {arg}')
  return func


COMMAND_MAP = {
    'INIT': do_send('initialize conversation'),
    'SAVE': do_send('save last message'),
    'REACT': do_react,
    'REPLY': do_reply,
    'SLEEP': do_sleep,
    'SLEPT': do_send('went offline for duration:'),
    'SAVE': do_send('save last message'),
    'PHOTO': do_send('send photo:'),
    'VIDEO': do_send('send video:'),
    'MEME': do_send('send meme:'),
}


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
  global NAME_MAP

  NAME_MAP[client.user.id] = NAME_MAP[0]
  del NAME_MAP[0]

  print(f"Logged in as {client.user}")
  # print(GPT_3("max: Depends on the drinks\ncameron: For sure jaya \ud83d\udc80\ud83d\udc80\nmax: That was max\ncameron: Implying you are not max?\nmax: I am max\nmax: Max is me\nmax: PHOTO photo of max taken by jaya\nmax: Me\n\n"))


def name_from_user(member):
  return NAME_MAP.get(member.id, member.display_name).lower()


conversations = {}


@client.event
async def on_message(message):
  conversation_id = f'{message.channel.id}%{message.guild.id}'
  conversation = conversations.get(
      conversation_id, Conversation(CONVERSATION_TIMEOUT, message.channel))

  username = name_from_user(message.author)

  # https://stackoverflow.com/questions/12597370/python-replace-string-pattern-with-output-of-function
  def replacer(match):
    return name_from_user(message.guild.get_member(int(match.group(1))))
  content = re.sub(r'<@(.+?)>', replacer, message.content.replace('\n', ' '))

  # TODO: media / pictures

  # TODO: timeout?

  if message.author.id != client.user.id:
    conversation = conversation.with_message(
        username, content, time.time())

  prediction = GPT_3(
      conversation.get_conversation(NUM_MESSAGES) + '\n\n')

  print(conversation.get_conversation(
      NUM_MESSAGES) + '\n\n', end='')
  print(prediction, end='')
  print('\n\n', end='')

  bot_name = name_from_user(client.user)
  if prediction.startswith(f'{bot_name}: '):
    response = prediction.replace(f'{bot_name}: ', '')
    conversation = conversation.with_message(bot_name, response, time.time())

    # TODO: refactor code below
    for command_id, command_fn in COMMAND_MAP.items():
      if response.startswith(command_id):
        command_token = f'{command_id} '
        await command_fn(message, response.replace(command_token, ''))
        break
    else:
      async with message.channel.typing():
        typing_delay = len(response) / TYPING_SPEED
        await asyncio.sleep(typing_delay)
      await message.channel.send(response)

  conversations[conversation_id] = conversation


openai.api_key = API_KEY
client.run(BOT_TOKEN)
