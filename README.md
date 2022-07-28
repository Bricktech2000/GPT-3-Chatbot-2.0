# GPT-3 Chatbot 2.0

A chatbot based on GPT-3 to replace our friend Grace on Discord

## Overview

This chatbot uses transcribed real-world conversations and generates training data to build a custom OpenAI GPT-3 model. Then, it uses the [Discord API](https://discord.com/developers/docs/) to send messages on Discord servers and tries to imitate the way a specific person would talk.

We currently use this bot on our servers to replace our friend Grace, who decided against getting a Discord account.

## Transcribing Conversation Data

Conversation data has been removed from the repository for privacy reasons. Therefore, you must create your own dataset to use this bot.

Create a markdown file called `howto/transcribed-conversation-data.md` containing conversation data in the following format:

```markdown
# START

## date1

username1: INIT;

username1: message1

username1: message2

username2: message3

username1: message4

...

## date2

username3: INIT;

...

#
```

The format of the data is very important:

- Whenever someone begins a new conversation, it must be preceded by a `username: INIT;` line.
- Every line must be seperated by two newlines and the file must start with `# START` and end with `#`.
- Special commands are to be used whenever a user sends multimedia, replies to a message, reacts to a message, and so on. Notice that commands with an argument end with `:` whereas commands without an argument end with `;`. A sample conversation is provided below.

The current training data is over 5000 words long. The longer it is, the more accurate the model will be.

### Example Conversation Data

Below is a made-up conversation as an example

```markdown
# START

## date3

emilien: INIT;

emilien: hi, how are you?

grace: REACT: ❤️

grace: I am good, and you?

emilien: I am good too

emilien: look at my awesome cat

emilien: PHOTO: emilien's cat on a leather sofa

emilien: VIDEO: emilien's cat walking around on a hard wood floor

grace: SAVE;

grace: SAVE;

grace: don't mind me saving those messages!

emilien: REPLY: I knew you would!

#
```

Note that `username: PHOTO;` and `username: VIDEO;` can be used to represent sending a photo or video without any description. Additionally, `username: SCREEN: description` and `username: MEME: description` can be used to represent sending a screenshot and a meme, respectively.

## Generating Custom OpenAI Model

After acquiring an [OpenAI API key](https://openai.com/api-keys), run the following commands to generate a custom OpenAI model in the `howto` folder:

```bash
export OPENAI_API_KEY=<OPENAI_API_KEY>

python3 conversation_data_to_openai_training_data.py # format training data for OpenAI
openai tools fine_tunes.prepare_data -f compiled-openai-training-data.jsonl # make sure no warnings are output

openai api fine_tunes.create -t "compiled-openai-training-data.jsonl" -m curie --n_epochs 4 # train the custom model
```

Note that you will be billed around 1$ for 5000 words worth of training data.

Take note of the model name that was generated, as you will need it for the next steps.

## Running the Bot

Start by installing all required dependencies:

```bash
pip install discord openai
```

Then, change the contents of the `username_map.json` file to map Discord user IDs to the names used in the training data. The user to be imitated must have its user ID set to `0`.

Finally, run the bot using a [Discord bot token](https://discord.com/developers/applications/), an [OpenAI API key](https://openai.com/api/) and the OpenAI model name generated previously.

```bash
python3 python main.py <Discord bot token> <OpenAI API key> <OpenAI model name>
```

## Credits

This bot is inspired by a similar chatbot two friends and I worked on: <https://github.com/Bricktech2000/GPT-3-Conversational-Bot>
