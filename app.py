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


import bot_types
import extentions
import settings
from subprocess import call
from os.path import exists as path_exists, basename
import cherrypy
from cherrypy.lib.static import serve_file
from tempfile import NamedTemporaryFile
from pymongo import MongoClient

call('nohup python bot.py &\necho $! > pid', shell=True)


class WebApp(object):
    def __init__(self):
        self.db = MongoClient(settings.Data.CONNECTION_STRING)[settings.Data.DB_NAME][settings.Data.TABLE_NAME]

    @cherrypy.expose
    def index(self):
        if path_exists('pid'):
            return 'Working ok.'
        else:
            return 'Not working.'

    @cherrypy.expose
    def inline(self, text, chat_id):
        chat_settings = bot_types.ChatSettings.from_dict(self.db.find_one({'_id': int(chat_id)}))

        with NamedTemporaryFile(suffix='.mp3' if chat_settings.as_audio else '.ogg') as file:
            bot_types.Speech.tts(extentions.TextHelper.unescape(text), chat_settings, file_like=file)
            file.seek(0)
            return serve_file(
                file.name,
                'audio/x-mpeg-3' if chat_settings.as_audio else 'audio/ogg'
            )

cherrypy.config.update({
    'server.socket_port': settings.Server.PORT,
    'server.socket_host': settings.Server.HOST
})

cherrypy.quickstart(WebApp())
