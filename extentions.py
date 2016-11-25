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
from telegram.ext import CallbackQueryHandler, Handler
from urllib.parse import quote as url_quote
from string import ascii_lowercase, digits
from random import SystemRandom
from bs4 import BeautifulSoup
from telegram import Update
from hashlib import md5
from enum import Enum

random = SystemRandom()


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


class UrlHelper(object):
    @staticmethod
    def try_custom_text_from_url(url: str):
        url_text = None
        if 'vk.com' in url and ('page' not in url or 'topic' not in url):
            if 'm.vk.com' in url:
                url = url.replace('m.vk.com', 'vk.com')

            url_text = BeautifulSoup(requests.get(url).text).body.find(
                'div',
                attrs={'class': 'pi_text'}
            ).text
        elif 'geektimes.ru' in url or 'habrahabr.ru' in url:
            if 'm.geektimes.ru' in url:
                url = url.replace('m.geektimes.ru', 'geektimes.ru')
            if 'm.habrahabr.ru' in url:
                url = url.replace('m.habrahabr.ru', 'habrahabr.ru')

            url_text = BeautifulSoup(requests.get(url).text).body.find(
                'div',
                attrs={'class': 'content html_format'}
            ).text
        elif 'livejournal.com' in url:
            url_text = BeautifulSoup(requests.get(url).text).body.find(
                'div',
                attrs={'class': 'asset-body'}
            ).text
        else:
            try:
                url_text = BeautifulSoup(requests.get(url).text).body.find(
                    'div',
                    attrs={'itemprop': 'articleBody'}
                ).text
            except:
                pass

        return url_text

    @staticmethod
    def prepare_url(url: str):
        url = url.replace(' ', '')
        if not url.startswith('http'):
            url = 'http://' + url
        if 'wikipedia' in url:
            url = url.replace('%20', '_').replace(' ', '_')

        return url


class TextHelper(object):
    @staticmethod
    def unescape(text: str):
        soup = BeautifulSoup(text)
        return soup.text

    @staticmethod
    def escape(text: str, safe: str = None):
        if safe is not None:
            return url_quote(text, safe=safe)
        else:
            return url_quote(text)

    @staticmethod
    def get_md5(data: str):
        data = data.encode('utf-8')
        m = md5(data)
        return m.hexdigest()

    @staticmethod
    def get_random_id(lenght: int = 16):
        return ''.join(random.choice(ascii_lowercase + digits) for _ in range(lenght))
