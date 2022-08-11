import math
import discord
import openai
import json
import asyncio
import sys
import re
import time
import random
import io
import aiohttp
from dalle2 import Dalle2
from conversation import ConversationManager

if len(sys.argv) != 5:
  print('Error: Usage: python3 main.py <Discord bot token> <OpenAI API key> <OpenAI model name> <OpenAI Dall-E bearer token>')
  exit(1)

# https://stackoverflow.com/questions/64221377/discord-py-rewrite-get-member-function-returning-none-for-all-users-except-bot
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.reactions = True
client = discord.Client(intents=intents)

BOT_TOKEN = sys.argv[1]
OPENAI_API_KEY = sys.argv[2]
OPENAI_ENGINE = sys.argv[3]
OPENAI_DALLE_TOKEN = sys.argv[4]

NUM_MESSAGES = 8  # the number of messages to append to the training data
TEMPERATURE = 0.8  # the "originality" of GPT-3's answers
MAX_TOKENS = 50  # the maximal length of GPt-3's answers
TYPING_SPEED = 15  # characters per second
CONVERSATION_TIMEOUT = 120  # seconds, time for a conversation to be considered dead
SERIALIZE_PATH = 'conversations.json'  # the path to serialize conversations


def name_from_member(member):
  with open('username_map.json', 'r') as f:
    username_map = json.load(f)
    id = member.id if member.id != client.user.id else 0
    return username_map.get(id, member.display_name).lower()


def function_from_command(command=None):
  async def do_react(message, conversation, save, arg):
    save(conversation)
    await message.add_reaction(arg)

  async def do_reply(message, conversation, save, arg):
    save(conversation)
    await message.reply(arg)

  async def do_sleep(message, conversation, save, arg, go_offline=True, min=30, max=1*60*60):
    # 30 seconds to 1 hour
    # https://stackoverflow.com/questions/49286640/how-to-set-bots-status
    # https://stackoverflow.com/questions/65773693/how-to-set-an-invisible-status-using-discord-py

    # make it more likely to sleep for less time
    n = 10
    delay = math.pow(random.uniform(math.pow(min, 1/n), math.pow(max, 1/n)), n)

    print(f'Notice: Bot is sleeping for {round(delay)}s')
    if go_offline:
      await client.change_presence(status=discord.Status.offline)
    await asyncio.sleep(delay)
    if go_offline and message.guild.get_member(client.user.id).status == discord.Status.online:
      return
    await client.change_presence(status=discord.Status.online)

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

  def do_media(media_type):
    async def func(message, conversation, save, arg):
      save(conversation)

      # https://stackoverflow.com/questions/68189435/how-to-make-discord-bot-send-images-from-an-online-link-python
      async with aiohttp.ClientSession() as session:
        async with session.get(DALLE_2(f'{media_type} {arg}')) as resp:
          if resp.status != 200:
            print(f'Error: DallE returned status code {resp.status}')
            return
          data = io.BytesIO(await resp.read())
          await message.channel.send(file=discord.File(data, f'{arg}.png'))

    return func

  COMMAND_MAP = {
      'INIT;': do_sleep,
      'SAVE;': do_nothing,
      'REACT: ': do_react,
      'REPLY: ': do_reply,
      'PHOTO: ': do_media('photo of '),
      'VIDEO: ': do_media('video of '),
      'PHOTO;': do_log('send random photo'),
      'VIDEO;': do_log('send random video'),
      'MEME: ': do_media('meme of '),
      'SCREEN: ': do_log('send screenshot:'),
      '': do_send
  }

  return COMMAND_MAP[command] if command is not None else COMMAND_MAP


def GPT_3(messages):
  response_object = openai.Completion.create(
      engine=OPENAI_ENGINE,
      prompt=messages,
      temperature=TEMPERATURE,
      max_tokens=MAX_TOKENS,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0.6,
      stop=['\n'],
  )

  # remove whitespace recommended by OpenAI
  return str(response_object['choices'][0]['text'])[1:]

def DALLE_2(description):
  # dalle 2 python api
  # https://pythondig.com/r/use-dalle--in-python
  # https://pypi.org/project/dalle2/1.0.8/

  dalle2 = Dalle2(OPENAI_DALLE_TOKEN)
  response_object = dalle2.generate(description)

  return response_object[0]['generation']['image_path']


conversation_manager = ConversationManager(
    CONVERSATION_TIMEOUT, SERIALIZE_PATH)


@client.event
async def on_ready():
  print(f'Logged in as {client.user}')

  # randomly initiate a conversation
  while True:
    await asyncio.sleep(1)
    random_channel_id, random_guild_id = random.choice(
        conversation_manager.get_all_ids() or [[None, None]])

    # wait for conversation_manager to have a conversation available
    if random_channel_id is None:
      continue

    conversation, save = conversation_manager.get(
        random_channel_id, random_guild_id)
    # add a temporary message because `do_sleep` will remove the last message
    conversation = conversation.with_message(
        ' ', ' ', time.time())
    channel = client.get_channel(int(random_channel_id))
    last_message = (await channel.history(limit=1).flatten())[0]

    # 5 hours to 20 hours
    await function_from_command('INIT;')(last_message, conversation, save, None, go_offline=False, min=5*60*60, max=20*60*60)


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
  # return if the bot is sleeping, but with a certain probability to go back online
  if message.guild.get_member(client.user.id).status != discord.Status.online and not random.random() < 0.125:
    return

  prediction = GPT_3(
      conversation.get_last_messages(NUM_MESSAGES) + '\n\n')

  if message.content.startswith('OVERRIDE: '):
    prediction = f"{name_from_member(client.user)}: {message.content.replace('OVERRIDE: ', '')}"

  # print(conversation.get_last_messages(NUM_MESSAGES) + '\n\n', end='')
  # print(prediction, end='')
  # print('\n\n')
  print(f'Prediction: {prediction}')

  match = re.search(
      f"^(.+?): ({'|'.join(function_from_command())})(.*?)$", prediction)
  if match:
    # prediction is correctly formed
    res_name, command, arg = match.group(1), \
        match.group(2), match.group(3)

    if res_name == name_from_member(client.user) or command == 'INIT;':
      # GPT-3 predicts bot should take action
      if message.guild.get_member(client.user.id).status != discord.Status.online:
        await client.change_presence(status=discord.Status.online)

      conversation, save = conversation_manager.get(
          message.channel.id, message.guild.id)

      conversation = conversation.with_message(
          name_from_member(client.user), f'{command}{arg}', time.time())

      await function_from_command(command)(message, conversation, save, arg)


openai.api_key = OPENAI_API_KEY
client.run(BOT_TOKEN)
