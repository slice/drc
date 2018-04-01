import logging
import sys
from collections import defaultdict, namedtuple
from typing import Any, Dict, List

import multio
from curious import Client

User = namedtuple('user', 'nick username host')


def parse_mask(name: str) -> User:
    nick, rest = name.split('!')
    username, host = rest.split('@')
    return User(nick=nick, username=username, host=host)


class IRC:
    def __init__(self, host: str, port: int, *, nick: str = None, autojoin: List[str] = None, bot: Client,
                 config: Dict[str, Any]):
        self.log = logging.getLogger(__name__)
        self.host = host
        self.port = port
        self.stream = None
        self.buffer_size = 16384
        self.autojoin = autojoin or []
        self.nick = nick or 'drc'
        self.bot = bot
        self.config = config
        self.events = defaultdict(list)

    def on(self, event_name: str):
        def decorator(handler):
            self.events[event_name].append(handler)
            return handler
        return decorator

    async def dispatch(self, event_name: str, *args, **kwargs):
        for handler in self.events[event_name]:
            await handler(*args, **kwargs)

    async def start(self):
        self.stream = await multio.open_connection(self.host, self.port)
        async with multio.task_manager() as manager:
            manager.start_soon(self.loop)
            manager.start_soon(self._startup)

    async def send(self, message: str):
        self.log.debug('send: %s', message)
        message_nl = f'{message}\r\n'
        await self.stream.send_all(message_nl.encode())

    async def _startup(self):
        await multio.sleep(1)  # wait a bit
        self.log.info('Going to identify.')
        await self.identify(self.nick, servername=self.nick, realname=self.nick)
        await multio.sleep(1)
        await self.send(f'MODE {self.nick} +B')
        for channel in self.autojoin:
            await self.join(channel)

    async def nickserv_identify(self):
        await self.privmsg('NickServ', f'IDENTIFY {self.config["irc"]["password"]}')

    async def register(self):
        password = self.config['irc']['password']
        email = self.config['irc']['email']
        await self.privmsg('NickServ', f'REGISTER {password} {email}')

    async def privmsg(self, target: str, message: str):
        await self.send(f'PRIVMSG {target} :{message}')

    async def identify(self, nick: str, *, servername: str, realname: str):
        await self.send(f'NICK {nick}')
        await self.send(f'USER {nick} 0.0.0.0 {servername} :{realname}')

    async def join(self, channel: str):
        await self.send(f'JOIN {channel}')

    async def loop(self):
        async with self.stream:
            while True:
                data = await self.stream.receive_some(self.buffer_size)
                message = data.decode()
                await self.handle_message(message)
                if not data:
                    self.log.error('Connection to %s has died.', self.host)
                    sys.exit()

    async def handle_message(self, message: str):
        self.log.debug('recv: %s', message.strip('\r\n'))

        tokens = message.split(' ')

        if any(token == 'PRIVMSG' for token in tokens):
            colon_parts = message.split(':')
            author = parse_mask(tokens[0][1:])
            location = tokens[2]
            message = ':'.join(colon_parts[2:])
            self.log.info('msg: [%s] <%s> %s', location, author.nick, message)
            await self.dispatch('privmsg', location, author, message)

        if 'You have not registered' in message:
            self.log.info('Automatically registering with NickServ.')
            await self.register()
            await multio.sleep(5)
            self.log.info('*** Automatically registered, please restart the bot! ***')
            sys.exit(0)
        elif 'This nickname is registered and protected.' in message:
            self.log.info('IDENTIFYing with NickServ.')
            await self.nickserv_identify()

        if message.startswith('PING'):
            await self.send('PONG ' + message[5:])
