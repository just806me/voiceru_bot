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

from os.path import dirname, realpath, join as path_join
from os import environ

# noinspection PyPep8
WEB_URI_REGEX = r'''(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))'''


class Telegram(object):
    DEV_TOKEN = None # Insert telegram token for development here
    TOKEN = None # Insert telegram token here
    GROUP_TOKEN = None # Insert telegram token here
    ADMIN_USERNAME = None # Insert admin username here
    ADMIN_ID = None # Insert admin id here
    BOT_ID = None # Insert bot id here
    BOT_GROUP_ID = None # Insert bot id here
    BOT_DEV_ID = None # Insert bot id for development here
    INLINE_CACHE_TIME = 30
    INLINE_WAIT_TIME = 3
    INLINE_URL = None + 'inline?text=%s&chat_id=%s&query_id=%s' # Insert url for inline mode here


class Data(object):
    CONNECTION_STRING = None # Insert mongodb connection string here
    DB_NAME = None # Insert datebase name here
    TABLE_NAME = None # Insert table name here


class Botan(object):
    TOKEN = None # Insert botan token here
    TRACK_URL = 'https://api.botan.io/track'
    SHORTENER_URL = 'https://api.botan.io/s/'


class Speech(object):
    class Yandex(object):
        TTS_URL = 'https://tts.voicetech.yandex.net/generate'
        STT_HOST = 'asr.yandex.net'
        STT_PATH = '/asr_xml'
        CHUNK_SIZE = 1024 ** 2
        TEXT_MAX_LEN = 2000

    class Ivona(object): # edit
        ACCESS_KEY = None # Insert ivona key here
        SECRET_KEY = None # Insert ivona secret here


class AudioTools(object):
    DIRECTORY = None # Insert /path/to/dir with ffmpeg, ffprobe, mp3val here


class Logging(object):
    ENDPOINT_HOST = None # Insert logging remote host here
    ENDPOINT_PATH = None # Insert logging remote path here
    LOG_FILE_PATH = None # Insert logging path/to/file here


class Server(object):
    HOST = None # Insert server ip here
    PORT = None # Insert server port here

