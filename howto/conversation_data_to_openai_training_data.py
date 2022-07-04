import json

training_data_length = 8


with open('transcribed-conversation-data.md', 'r') as f:
  data_conversations = f.read()

data_lines = list(
    filter(lambda line: not line.startswith('#'),
           data_conversations.split('# START')[1].split('\n\n'))
)

openai_data_arr = [{
    'prompt': '\n'.join(data_lines[l:l+training_data_length]) + '\n\n',
    # whitespace character recommended by OpenAI at begining of all completions
    'completion': ' ' + data_lines[l+training_data_length] + '\n'
} for l in range(len(data_lines) - training_data_length)]

# OpenAI recommendation
assert not any(('\n' in data['completion'][1:-1] or not data['completion'].endswith('\n'))
               and (print(data['completion']) or True) for data in openai_data_arr)

assert not any(('\n\n' in data['prompt'][:-2] or not data['prompt'].endswith('\n'))
               and (print(data['prompt']) or True) for data in openai_data_arr)

# JSONL format
openai_data = '\n'.join(map(json.dumps, openai_data_arr))
with open('compiled-openai-training-data.jsonl', 'w') as f:
  f.write(openai_data)
