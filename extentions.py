#!/usr/bin/env python
#
# @voiceru_bot Telegram bot app
# https://telegram.me/voiceru_bot
#
# Copyright (C) 2016
# Leonid Kuznetsov @just806me just806me@gmail.com
#
# This program is licensed under The MIT License (MIT)
# See https://opensource.org/licenses/MIT

import settings
import requests
import re
from telegram.ext import CallbackQueryHandler, Handler
from urllib.parse import quote, unquote
from string import ascii_lowercase, digits
from random import SystemRandom
from bs4 import BeautifulSoup
from telegram import Update
from hashlib import md5
from enum import Enum

random = SystemRandom()
TAG_RE = re.compile(r'<[^>]+>')
CLEAR_RE = re.compile('[^(\s\w!@#$%^&*()_+\\-=\[\]{};\':\"|,.<>\/?)]', re.UNICODE)
UUID4_RE = re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')


class MyCallbackQueryHandler(CallbackQueryHandler):
    def __init__(self, command, callback, pass_update_queue=False):
        super().__init__(callback, pass_update_queue)
        self.command = command

    def check_update(self, update: Update):
        return isinstance(update, Update) and update.callback_query and \
               update.callback_query.data and update.callback_query.data == self.command


class LambdaHandler(Handler):
    def __init__(self, delegate, callback, pass_update_queue=False):
        super(LambdaHandler, self).__init__(callback, pass_update_queue=pass_update_queue)
        self.check_update = delegate

    def handle_update(self, update, dispatcher):
        optional_args = self.collect_optional_args(dispatcher)

        self.callback(dispatcher.bot, update, **optional_args)


class EnumHelper(Enum):
    @staticmethod
    def parse(enum_type: Enum, value: str):
        if enum_type is None or value is None:
            return None
        for v in enum_type:
            if v.name == value:
                return v
        return None


class FileHelper(object):
    @staticmethod
    def read_chunks(chunk_size: int, filename: str = None, content: bytes = None):
        if filename is not None:
            file = open(filename, 'br')
            content = file.read()
            file.close()
        if content is None:
            raise Exception('No file name or content provided.')

        while True:
            chunk = content[:chunk_size]
            content = content[chunk_size:]

            yield chunk

            if not content:
                break


class TextHelper(object):
    @staticmethod
    def text_to_parts(text: str, part_length: int = settings.Speech.Yandex.TEXT_MAX_LEN):
        words = text.split()
        parts = ['']
        i = 0

        for w in words:
            tmp = w + ' '
            if len(TextHelper.escape(parts[i] + tmp, safe='').encode('utf-8')) <= part_length:
                parts[i] += tmp
            else:
                parts.append(tmp)
                i += 1

        return parts

    @staticmethod
    def unescape(text: str):
        return unquote(text)

    @staticmethod
    def remove_tags(text: str):
        return TAG_RE.sub('', text)

    @staticmethod
    def clear(text: str):
        return CLEAR_RE.sub('', text)

    @staticmethod
    def escape(text: str, safe: str = None):
        if safe is not None:
            return quote(text, safe=safe)
        else:
            return quote(text)

    @staticmethod
    def get_md5(data: str):
        data = data.encode('utf-8')
        m = md5(data)
        return m.hexdigest()

    @staticmethod
    def get_random_id(lenght: int = 16):
        return ''.join(random.choice(ascii_lowercase + digits) for _ in range(lenght))

    @staticmethod
    def words_count(text: str):
        return len(text.split(' '))

    @staticmethod
    def validate_uuidv4(data: str):
        return bool(UUID4_RE.match(data))
