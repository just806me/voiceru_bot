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

import xml.etree.ElementTree as XmlElementTree
import subprocess
import httplib2
import tempfile
import settings
import requests
import logging
import json
import os
from extentions import EnumHelper, FileHelper, TextHelper
from signal import signal, SIGINT, SIGTERM, SIGABRT
from pyvona import create_voice as ivona_voice
# noinspection PyPackageRequirements
from telegram.ext.dispatcher import run_async
from pymongo import MongoClient
from random import SystemRandom
from enum import Enum, unique
from time import time, sleep
# noinspection PyPackageRequirements
from telegram import Chat

random = SystemRandom()


@unique
class Voice(Enum):
    robot = 0
    zahar = 1
    ermil = 2
    jane = 3
    oksana = 4
    alyss = 5
    omazh = 6
    maxim = 7
    tatyana = 8

    def __str__(self):
        return self.name


@unique
class Emotion(Enum):
    good = 0
    evil = 1
    neutral = 2
    mixed = 3

    def __str__(self):
        if self.value == 0:
            return 'доброжелательный'
        elif self.value == 1:
            return 'злой'
        elif self.value == 2:
            return 'нейтральный'
        elif self.value == 3:
            return 'переменный'
        else:
            return None


@unique
class Mode(Enum):
    tts = 0
    stt = 1
    both = 2

    def __str__(self):
        if self.value == 0:
            return 'текст в речь'
        elif self.value == 1:
            return 'речь в текст'
        elif self.value == 2:
            return 'текст в речь и речь в текст'
        else:
            return None


@unique
class ChatInputState(Enum):
    normal = 0
    input_speed = 1
    input_donate = 2
    input_url = 3


class ChatSettings(object):
    def __init__(self, db = None, chat: Chat = None, voice: Voice = Voice.robot, speed: float = 1.0,
                 emotion: Emotion = Emotion.good, first_time: int = time(), active_time: int = 0,
                 active_time_inline: int = 0, as_audio: bool = False, mode: Mode = Mode.both, admin_id: int = None,
                 admin_name: str = None, admin_only: bool = False, quiet: bool = False,
                 donate_sum: int = 0, donate: bool = False):
        if chat:
            self.id = chat.id

            if hasattr(chat, 'username') and chat.username:
                self.tg_name = chat.username
            elif hasattr(chat, 'title') and chat.title:
                self.tg_name = chat.title
            elif hasattr(chat, 'first_name') and chat.first_name:
                self.tg_name = chat.first_name
            else:
                self.tg_name = ''

            self.tg_name = self.tg_name

            self.voice = voice
            self.speed = speed
            self.emotion = emotion
            self.first_time = first_time
            self.active_time = active_time
            self.active_time_inline = active_time_inline
            self.as_audio = as_audio
            self.mode = mode
            self.admin_id = admin_id
            self.admin_name = admin_name if admin_name else None
            self.admin_only = admin_only
            self.quiet = quiet
            self.donate_sum = donate_sum
            self.donate = donate
        else:
            self.id = None
            self.tg_name = None
            self.voice = None
            self.speed = None
            self.emotion = None
            self.first_time = None
            self.active_time = None
            self.active_time_inline = None
            self.as_audio = None
            self.mode = None
            self.admin_id = None
            self.admin_name = None
            self.admin_only = None
            self.quiet = None
            self.donate_sum = None
            self.donate = None
        if db:
            db.insert_one(self.to_dict())

    @staticmethod
    def from_dict(value: dict):
        chat_settings = ChatSettings()

        chat_settings.id = value['_id']
        chat_settings.tg_name = TextHelper.unescape(value['tg-name'])
        chat_settings.voice = EnumHelper.parse(Voice, value['voice']) if 'voice' in value else Voice.robot
        chat_settings.speed = float(value['speed']) if 'speed' in value else 1.0
        chat_settings.emotion = EnumHelper.parse(Emotion, value['emotion']) if 'emotion' in value else Emotion.good
        chat_settings.first_time = int(value['first-time']) if 'first-time' in value else time()
        chat_settings.active_time = int(value['active-time']) if 'active-time' in value else 0
        chat_settings.active_time_inline = int(value['active-time-inline']) if 'active-time-inline' in value else 0
        chat_settings.as_audio = bool(value['audio']) if 'audio' in value else False
        chat_settings.mode = EnumHelper.parse(Mode, value['mode']) if 'mode' in value else Mode.both
        chat_settings.admin_id = int(value['admin-id']) if 'admin-id' in value and value['admin-id'] != 0 else None
        chat_settings.admin_name = TextHelper.unescape(str(value['admin-name'])) if 'admin-name' in value else None
        chat_settings.admin_only = bool(value['admin-only']) if 'admin-only' in value else False
        chat_settings.quiet = bool(value['quiet']) if 'quiet' in value else False
        chat_settings.donate_sum = int(value['donate-sum']) if 'donate-sum' in value else 0
        chat_settings.donate = bool(value['donate']) if 'donate' in value else False

        return chat_settings

    def to_dict(self):
        return {
            '_id': self.id,
            'tg-name': TextHelper.escape(self.tg_name),
            'voice': self.voice.name,
            'speed': self.speed,
            'emotion': self.emotion.name,
            'first-time': self.first_time,
            'active-time': self.active_time,
            'active-time-inline': self.active_time_inline,
            'audio': self.as_audio,
            'mode': self.mode.name,
            'admin-id': self.admin_id if self.admin_id is not None else 0,
            'admin-name': TextHelper.escape(self.admin_name) if self.admin_name is not None else 'None',
            'admin-only': self.admin_only,
            'quiet': self.quiet,
            'donate-sum': self.donate_sum,
            'donate': self.donate
        }

    @staticmethod
    def from_db(db: MongoClient, chat: Chat, admin_id: int = None, admin_name: str = None):
        from_db = db.find_one({'_id': chat.id})

        if from_db:
            return ChatSettings.from_dict(from_db)
        else:
            return ChatSettings(db, chat, admin_id=admin_id, admin_name=admin_name)


class Donate(object):
    @staticmethod
    def get_url(donate_sum, pay_type='AC'):
        return settings.Donate.URL + \
               '?receiver=%s&formcomment=%s&short-dest=%s&quickpay-form=%s' \
               '&targets=%s&paymentType=%s&sum=%s&successURL=%s' % (
                   # receiver
                   settings.Donate.RECEIVER,
                   # sender history name
                   settings.Donate.TITLE,
                   # confirm name
                   settings.Donate.TITLE,
                   # transaction type
                   'donate',
                   # target
                   settings.Donate.TARGET,
                   # payment type
                   pay_type,
                   # sum
                   donate_sum,
                   # success url
                   settings.Donate.SUCCESS_URL
               )


class Botan(object):
    @staticmethod
    @run_async
    def track(uid, message=None, name='Message', token=settings.Botan.TOKEN):
        requests.post(
            settings.Botan.TRACK_URL,
            params={"token": token, "uid": uid, "name": name},
            data=json.dumps(message) if message else '{}',
            headers={'Content-type': 'application/json'},
        )

    # noinspection PyBroadException
    @staticmethod
    def shorten_url(uid, url, token=settings.Botan.TOKEN):
        try:
            r = requests.get(settings.Botan.SHORTENER_URL, params={
                'token': token,
                'url': url,
                'user_ids': str(uid),
            })

            if r.status_code == 200:
                return r.text
            else:
                raise Exception('Botan: bad status code - %s' % str(r.status_code))
        except:
            return url


class Addybot(object):
    # noinspection PyBroadException
    @staticmethod
    def get_advertisement(uid):
        data = json.dumps({'userIdentifier': str(uid), 'language': 'russian'}).encode('utf-8')
        r = json.loads(requests.post(
            url=settings.Addybot.API_URL % settings.Addybot.TOKEN,
            data=data,
            headers=settings.Addybot.HEADERS
        ).text)

        if r['responseType'] == 'success':
            return r['data']['text'], r['data']['uri']
        else:
            raise Exception(r['message'])


class Readability(object):
    @staticmethod
    def get_text_from_web_page(page_url: str):
        url = '%s/parser?token=%s&url=%s' % (
            # base_url
            settings.Readability.API_URL,
            # token
            settings.Readability.PARSER_TOKEN,
            # page_url
            page_url
        )

        response = requests.get(url)
        if response is not None and response.status_code == 200:
            data = json.loads(response.text)
            return data['content'], data['title']
        else:
            raise Exception('Cannot parse page at %s - bad response: %s' % (page_url, response.text))

    @staticmethod
    def get_confidence(page_url: str):
        url = '%s/confidence?url=%s' % (
            # base_url
            settings.Readability.API_URL,
            # page_url
            page_url
        )

        response = requests.get(url)
        if response is not None and response.status_code == 200:
            data = json.loads(response.text)
            return data['confidence']
        else:
            raise Exception('Cannot get confidence of page at %s - bad response: %s' % page_url, response.text)


class FfmpegWrap(object):
    @staticmethod
    def __convert__(command, in_filename: str = None, in_content: bytes = None):
        with tempfile.TemporaryFile() as temp_out_file:
            temp_in_file = None

            if in_content:
                temp_in_file = tempfile.NamedTemporaryFile(delete=False)
                temp_in_file.write(in_content)
                in_filename = temp_in_file.name
                temp_in_file.close()
            if not in_filename:
                raise Exception('Neither input file name nor input bytes is specified.')

            proc = subprocess.Popen(command(in_filename), stdout=temp_out_file, stderr=subprocess.DEVNULL)
            proc.wait()

            if temp_in_file:
                os.remove(in_filename)

            temp_out_file.seek(0)
            return temp_out_file.read()

    @staticmethod
    def convert_to_ogg(in_filename: str = None, in_content: bytes = None):
        command = lambda f: [
            os.path.join(settings.Ffmpeg.DIRECTORY, 'ffmpeg'),
            '-loglevel', 'quiet',
            '-i', f,
            '-f', 'ogg',
            '-acodec', 'libopus',
            '-'
        ]

        return FfmpegWrap.__convert__(command, in_filename, in_content)

    @staticmethod
    def convert_to_mp3(in_filename: str = None, in_content: bytes = None):
        command = lambda f: [
            os.path.join(settings.Ffmpeg.DIRECTORY, 'ffmpeg'),
            '-loglevel', 'quiet',
            '-i', f,
            '-f', 'mp3',
            '-acodec', 'libmp3lame',
            '-'
        ]

        return FfmpegWrap.__convert__(command, in_filename, in_content)

    @staticmethod
    def convert_to_pcm16b16000r(in_filename: str = None, in_content: bytes = None):
        command = lambda f: [
            os.path.join(settings.Ffmpeg.DIRECTORY, 'ffmpeg'),
            '-loglevel', 'quiet',
            '-i', f,
            '-f', 's16le',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-'
        ]

        return FfmpegWrap.__convert__(command, in_filename, in_content)

    @staticmethod
    def get_duration(file_path: str = None, audio_content: bytes = None):
        temp_file = None

        if audio_content:
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.write(audio_content)
            temp_file.close()

            file_path = temp_file.name

        ffmpeg_proc = subprocess.Popen(
            [os.path.join(settings.Ffmpeg.DIRECTORY, 'ffprobe'), file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        output = ffmpeg_proc.communicate()[0].decode('utf-8')
        duration = None
        for o in output.split('\n'):
            if 'Duration' in o and 'misdetection' not in o:
                duration = o.split()[1][:-1].split(':')  # here goes magic => time['h', 'm', 's']
                break
        if duration:
            duration = float(duration[0]) * 3600 + float(duration[1]) * 60 + float(duration[2])
            if duration < 1:
                duration = 1
        else:
            duration = 0

        if temp_file:
            os.remove(file_path)

        return duration


class Speech(object):
    # noinspection PyProtectedMember
    @staticmethod
    def tts(text: str, chat_settings: ChatSettings, lang: str = 'ru-RU', key: str = settings.Speech.Yandex.API_KEY,
            filename: str = None, file_like=None, convert: bool=True):
        if isinstance(text, bytes):
            text = text.decode('utf-8')

        if chat_settings.voice == Voice.maxim or chat_settings.voice == Voice.tatyana:
            if chat_settings.speed > 1.75:
                speech_rate = 'x-fast'
            elif chat_settings.speed > 1.25:
                speech_rate = 'fast'
            elif chat_settings.speed > 0.75:
                speech_rate = 'medium'
            elif chat_settings.speed > 0.25:
                speech_rate = 'slow'
            else:
                speech_rate = 'x-slow'

            v = ivona_voice(settings.Speech.Ivona.ACCESS_KEY, settings.Speech.Ivona.SECRET_KEY)
            v.codec = 'mp3'
            v.speech_rate = speech_rate
            v.voice_name = chat_settings.voice.name.capitalize()

            r = v._send_amazon_auth_packet_v4(
                'POST', 'tts', 'application/json', '/CreateSpeech', '',
                v._generate_payload(text), v._region, v._host
            )

            if r.content.startswith(b'{'):
                raise Exception('Error getting audio form ivona.')
            else:
                response_content = r.content
        else:
            url = settings.Speech.Yandex.TTS_URL + \
                  '?text=%s&format=%s&lang=%s&speaker=%s&key=%s&emotion=%s&speed=%s' % (
                      TextHelper.escape(text, safe=''),
                      'mp3',
                      lang,
                      chat_settings.voice.name,
                      key,
                      chat_settings.emotion.name,
                      str(chat_settings.speed)
                  )

            r = requests.get(url)
            if r.status_code == 200:
                response_content = r.content
            else:
                raise Exception('TTS Error: ' + r.text)

        if not chat_settings.as_audio and convert:
            response_content = FfmpegWrap.convert_to_ogg(in_content=response_content)

        if filename:
            with open(filename, 'bw') as file:
                file.write(response_content)
        elif file_like:
            file_like.write(response_content)

        return response_content

    @staticmethod
    def stt(filename: str = None, content: bytes = None, request_id: str = None, topic: str = 'notes',
            lang: str = 'ru-RU', key: str = settings.Speech.Yandex.API_KEY):
        if filename is not None:
            file = open(filename, 'br')
            content = file.read()
            file.close()
        if content is None:
            raise Exception('No file name or content provided.')

        content = FfmpegWrap.convert_to_pcm16b16000r(in_content=content)

        if request_id is not None:
            uuid = TextHelper.get_md5(request_id)
        else:
            uuid = TextHelper.get_md5(str(time()))

        url = settings.Speech.Yandex.STT_PATH + '?uuid=%s&key=%s&topic=%s&lang=%s' % (
            uuid,
            key,
            topic,
            lang
        )
        chunks = FileHelper.read_chunks(settings.Speech.Yandex.CHUNK_SIZE, content=content)

        connection = httplib2.HTTPConnectionWithTimeout(settings.Speech.Yandex.STT_HOST)

        connection.connect()
        connection.putrequest('POST', url)
        connection.putheader('Transfer-Encoding', 'chunked')
        connection.putheader('Content-Type', 'audio/x-pcm;bit=16;rate=16000')
        connection.endheaders()

        for chunk in chunks:
            connection.send(('%s\r\n' % hex(len(chunk))[2:]).encode('utf-8'))
            connection.send(chunk)
            connection.send('\r\n'.encode('utf-8'))
            sleep(1)

        connection.send('0\r\n\r\n'.encode('utf-8'))

        response = connection.getresponse()
        if response.code == 200:
            response_text = response.read()
            xml = XmlElementTree.fromstring(response_text)

            if int(xml.attrib['success']) == 1:
                max_confidence = - float("inf")
                text = ''

                for child in xml:
                    if float(child.attrib['confidence']) > max_confidence:
                        text = child.text
                        max_confidence = float(child.attrib['confidence'])

                if max_confidence != - float("inf"):
                    return text
                else:
                    raise Exception(
                        'STT: No text found.\n\nResponse:\n%s\n\nRequest id: %s' % (
                            response_text,
                            request_id if request_id is not None else 'None'
                        )
                    )
        else:
            raise Exception('STT: Yandex ASR bad response.\nCode: %s\n\n%s' % (response.code, response.read()))


# Adds 'id' property to record
class IdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'id'):
            record.id = 'None'
        return True


class UpdatersStack(object):
    def __init__(self, *updaters):
        self.updaters = list(updaters)

    def add_handlers(self, *handlers):
        for updater in self.updaters:
            for handler in handlers:
                updater.dispatcher.add_handler(handler)

    def idle(self, stop_signals=(SIGINT, SIGTERM, SIGABRT)):
        for updater in self.updaters:
            for sig in stop_signals:
                signal(sig, updater.signal_handler)
            updater.is_idle = self.is_idle

        while self.is_idle():
            sleep(1)

    def is_idle(self):
        is_idle = False
        for updater in self.updaters:
            if updater.is_idle:
                is_idle = True
                break

        return is_idle

    def start_polling(self, poll_interval=0.0, timeout=10, network_delay=5., clean=False, bootstrap_retries=0):
        for updater in self.updaters:
            updater.start_polling(poll_interval, timeout, network_delay, clean, bootstrap_retries)
