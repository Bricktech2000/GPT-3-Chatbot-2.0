import discord
import openai
import asyncio
import sys
import re
import time

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

NUM_CHATS = 8  # the number of chats to append to the training data
TEMPERATURE = 0.8  # the "originality" of GPT-3's answers
MAX_TOKENS = 50  # the maximal length of GPt-3's answers
TYPING_SPEED = 15  # characters per second
CONVERSATION_TIMEOUT = 10  # seconds, time for a conversation to be considered dead

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


def do_send(text):
  async def func(message, arg):
    await message.channel.send(f'**COMMAND: {text}** {arg}')
  return func


COMMAND_MAP = {
    'INIT': do_send('initialize conversation'),
    'SAVE': do_send('save last message'),
    'REACT': do_react,
    'REPLY': do_reply,
    'SLEEP': do_send('go offline for duration:'),
    'SLEPT': do_send('went offline for duration:'),
    'SAVE': do_send('save last message'),
    'PHOTO': do_send('send photo:'),
    'VIDEO': do_send('send video:'),
    'MEME': do_send('send meme:'),
}


# TODO: implement conversation class
conversation = []
last_message_timestamp = 0
conversation_channel = None


def GPT_3(conversation):
  response_object = openai.Completion.create(
      engine=ENGINE,
      prompt=conversation,
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


@client.event
async def on_message(message):
  global last_message_timestamp
  global conversation

  username = name_from_user(message.author)

  # https://stackoverflow.com/questions/12597370/python-replace-string-pattern-with-output-of-function
  def asdf(match):
    return name_from_user(message.guild.get_member(int(match.group(1))))
  content = re.sub(r'<@(.+?)>', asdf, message.content.replace('\n', ' '))

  # TODO: media / pictures

  # TODO: timeout?

  if last_message_timestamp + CONVERSATION_TIMEOUT < time.time():
    conversation.append(f'{username}: INIT')
  if message.author.id != client.user.id:
    conversation.append(f'{username}: {content}')
  last_message_timestamp = time.time()
  conversation_channel = None

  prediction = GPT_3('\n'.join(conversation[-NUM_CHATS:]) + '\n\n')

  print('\n'.join(conversation[-NUM_CHATS:]) + '\n\n')
  print(prediction)

  start_token = f'{NAME_MAP[client.user.id]}: '
  if prediction.startswith(start_token):
    conversation.append(prediction)
    response = prediction.replace(start_token, '')

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


openai.api_key = API_KEY
client.run(BOT_TOKEN)
