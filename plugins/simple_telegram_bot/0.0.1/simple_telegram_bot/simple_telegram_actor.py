import asyncio
import hashlib
import logging
import os

from aiogram import Dispatcher, Bot, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


dispatcher = Dispatcher()


class SimpleTelegramActor:

    def __init__(self):
        self.adaptor = None
        self.page_size = 5
        self._chats = {}
        self._dispatcher = dispatcher
        self._dispatcher['actor'] = self
        self._bot = None
        self._telegram = None

    async def exit(self):
        for chat_id in self._chats:
            try:
                await self._bot.send_message(chat_id, "⚠️ Bot is stopped!")
            except Exception as e:
                logging.exception(e)
        if self._telegram:
            await self._dispatcher.stop_polling()
        if self._telegram:
            self._telegram.cancel()
            await asyncio.wait_for(self._telegram, 2)

    async def handle(self, msg):
        command = msg.get('command')
        body = msg.get('body') if msg.get('body') else {}
        sender = msg.get('sender')
        if command == 'set_params':
            await self.set_params(body.get('params'), sender)
        elif command == 'start':
            await self.start(sender)
        else:
            return False
        return True

    async def set_params(self, params, recipient):
        self.adaptor.set_params(params)
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('params_are_set', recipient=recipient))

    async def start(self, recipient):
        credentials = await self.adaptor.get_credentials('telegram')
        token = os.environ.get('TELEGRAM', credentials.get('password'))
        self._bot = Bot(token=token)
        self._telegram = asyncio.get_running_loop().create_task(
            self._dispatcher.start_polling(self._bot, handle_signals=False)
        )
        if recipient:
            await self.adaptor.send(self.adaptor.get_msg('telegram_is_started', None, recipient))

    async def process(self, param):
        request = await self.get_request(param)
        if not request:
            return
        builder = InlineKeyboardBuilder()
        buttons = {}
        level = await self.make_menu(builder, buttons, request)
        chat_id = message_id = None
        if isinstance(param, Message):
            message = await param.answer(level, reply_markup=builder.as_markup())
            chat_id = message.chat.id
            message_id = message.message_id
        elif isinstance(param, CallbackQuery):
            message = param.message
            chat_id = message.chat.id
            message_id = message.message_id
            await message.edit_text(level, reply_markup=builder.as_markup())
        elif isinstance(param, int):
            if not self.are_buttons_equal(param, buttons):
                chat_id = param
                message_id = list(self._chats.get(chat_id))[0]
                await self._bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                                 text=level, reply_markup=builder.as_markup())
        if chat_id and message_id:
            self._chats[chat_id] = {message_id: {'buttons': buttons, 'request': request.get('body')}}

    async def get_request(self, param):
        body = None
        if isinstance(param, Message):
            body = {'page_size': self.page_size, 'level': None, 'id': None, 'recipient': self.adaptor.get_head_addr()}
        if isinstance(param, CallbackQuery):
            body = self.get_request_for_query(param)
            if not body:
                await param.answer('Not handled')
        elif isinstance(param, int):
            body = self.get_request_for_refresh(param)
        if not body:
            return None
        return self.adaptor.get_msg('get_members', body, body.get('recipient'))

    def get_request_for_query(self, query):
        chat = self._chats.get(query.message.chat.id)
        if not chat:
            return None
        buttons = chat.get(query.message.message_id).get('buttons')
        if not buttons:
            return None
        button = buttons.get(query.data)
        level = button.get('next_level')
        if not level:
            return None
        return {'page_size': self.page_size, 'level': level, 'id': button.get('id'), 'recipient': button.get('recipient')}

    def get_request_for_refresh(self, chat_id):
        chat = self._chats.get(chat_id)
        if not chat:
            return None
        message_id = list(chat)[0]
        if not message_id:
            return None
        return chat.get(message_id).get('request')

    async def make_menu(self, builder, buttons, request):
        ans = await self.adaptor.ask(request)
        body = ans.get('body')
        level = body.get('level')
        member = body.get('_back')
        if member:
            self.add_menu_item(builder, buttons, member)
        for member in body.get('members'):
            self.add_menu_item(builder, buttons, member)
        nav = body.get('nav')
        builder.adjust(1)
        if nav:
            self.add_nav(builder, buttons, nav)
        return level

    def add_menu_item(self, builder, buttons, mbr):
        hsh = self.get_hash(mbr)
        text = '...' if mbr.get('id') == '_back' else mbr.get('id')
        builder.button(text=text, callback_data=hsh)
        buttons[hsh] = mbr

    def get_hash(self, mbr):
        key = str(mbr.get('next_level')) + str(mbr.get('recipient')) + str(mbr.get('id'))
        return hashlib.blake2s(key.encode(), digest_size=32).hexdigest()

    def add_nav(self, builder, buttons, nav):
        count = nav.get('count')
        page = nav.get('page')
        row = []
        if page > 0:
            self.add_nav_button(buttons, row, nav, f'_page_{page-1}', '<')
        self.add_nav_button(buttons, row, nav, f'_page_{page}', f'{page+1}', True)
        if page < count - 1:
            self.add_nav_button(buttons, row, nav, f'_page_{page+1}', '>')
        builder.row(*row)

    def add_nav_button(self, buttons, row, nav, xid, text, no_action=False):
        level = None if no_action else nav.get('next_level')
        mbr = {'next_level': level, 'recipient': nav.get('recipient'), 'id': xid}
        hsh = self.get_hash(mbr)
        row.append(InlineKeyboardButton(text=text, callback_data=hsh))
        buttons[hsh] = mbr

    def are_buttons_equal(self, chat_id, new_buttons):
        chat = self._chats.get(chat_id)
        if not chat:
            return None
        message_id = list(chat)[0]
        if not message_id:
            return None
        old_buttons = chat.get(message_id).get('buttons')
        return new_buttons.keys() == old_buttons.keys()

    async def handle_command(self, message, is_ask):
        args = message.text.split(maxsplit=1)
        params = args[1] if len(args) > 1 else None
        res = self.adaptor.json_loads(params)
        if not res:
            await message.answer('Wrong command format')
            return
        recipient = res.get('recipient') if res.get('recipient') else self.adaptor.get_head_addr()
        msg = self.adaptor.get_msg(res.get('command'), res.get('body'), recipient)
        if is_ask:
            ans = await self.adaptor.ask(msg, 20)
            await message.answer(self.adaptor.json_dumps(ans))
        else:
            await self.adaptor.send(msg)
            await message.answer('The message is sent')
        await self.process(message.chat.id)


@dispatcher.message(CommandStart())
async def command_start_handler(message: Message):
    await dispatcher.get('actor').process(message)


@dispatcher.callback_query()
async def update_menu(query: CallbackQuery):
    await dispatcher.get('actor').process(query)


@dispatcher.message(Command('ask'))
async def handle_ask(message: Message):
    await dispatcher.get('actor').handle_command(message, True)


@dispatcher.message(Command('send'))
async def handle_ask(message: Message):
    await dispatcher.get('actor').handle_command(message, False)


@dispatcher.message(F.text.startswith('/'))
async def handle_any_command(message: Message):
    await message.answer('Command is not exist')

@dispatcher.message()
async def handle_any_message(message: Message):
    await message.answer('Not handled')
