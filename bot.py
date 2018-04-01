import datetime
import logging

import multio
from curious.core.client import Client
from ruamel.yaml import YAML

from irc import IRC, User

with open('config.yml', 'r') as fp:
    config = YAML().load(fp)

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('lomond').setLevel(logging.WARNING)
logging.getLogger('curious').setLevel(logging.WARNING)
multio.init('trio')

bot = Client(config['discord']['token'])
bot.irc = IRC(
    config['irc']['host'], config['irc']['port'],
    autojoin=config['irc']['autojoin'],
    nick=config['irc'].get('nick'),
    bot=bot, config=config
)


@bot.irc.on('privmsg')
async def privmsg_handler(channel: str, author: User, message: str):
    dest = bot.find_channel(config['discord']['broadcast_channel'])
    clean_message = message.replace('@', '@\u200b').replace('`', '\N{MODIFIER LETTER GRAVE ACCENT}')[:1500]
    timestamp = datetime.datetime.utcnow().strftime('%H:%M:%S')
    forward = f'`[{timestamp}]` `[{channel}]` {author.nick} » {clean_message}'
    await dest.messages.send(forward)


async def run():
    async with multio.task_manager() as manager:
        manager.start_soon(bot.run_async)
        manager.start_soon(bot.irc.start)


multio.run(run)
