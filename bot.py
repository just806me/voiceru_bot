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

import logging.handlers as log_handlers
# noinspection PyPackageRequirements
import telegram.ext
import extentions
import bot_types
# noinspection PyPackageRequirements
import telegram
import requests
import tempfile
import settings
import strings
import logging
import re
# noinspection PyPackageRequirements
from telegram.ext.dispatcher import run_async
from pymongo import MongoClient
from time import time, gmtime
from queue import Queue


# region logs setup

def loggly_format(record):
    if record.levelname == logging.ERROR:
        bot_types.Botan.track(
            uid=0,
            name='Unknown error'
        )
    return {
        'Type': record.levelname,
        'Id': record.id,
        'From': {
            'File': record.pathname,
            'Module': record.module,
            'Function': record.funcName,
            'Line': record.lineno
        },
        'Timestamp': record.created,
        'Message': record.msg,
        'Exception': record.exc_text if record.exc_text else 'None',
        'Telegram': record.telegram if hasattr(record, 'telegram') else 'None'
    }
loggly_handler = log_handlers.HTTPHandler(settings.Logging.ENDPOINT_HOST, settings.Logging.ENDPOINT_PATH, 'POST', True)
loggly_handler.mapLogRecord = loggly_format
loggly_handler.setLevel(logging.INFO)
loggly_handler.addFilter(bot_types.IdFilter())

file_handler = log_handlers.RotatingFileHandler(settings.Logging.LOG_FILE_PATH, maxBytes=10 * (1024**2), backupCount=9)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('[ %(asctime)s\t%(levelname)s\t%(module)s ]:\n%(id)s - %(message)s\n'))
file_handler.addFilter(bot_types.IdFilter())

logging_queue = Queue()
queue_handler = log_handlers.QueueHandler(logging_queue)
queue_listener = log_handlers.QueueListener(logging_queue, loggly_handler, file_handler)

logging.basicConfig(level=logging.INFO)
logging.Formatter.converter = gmtime

logger = logging.getLogger()
logger.addHandler(queue_handler)

queue_listener.start()

# endregion

db = MongoClient(settings.Data.CONNECTION_STRING)[settings.Data.DB_NAME][settings.Data.TABLE_NAME]

# 29 is '@run_async' count
if settings.Telegram.DEV_TOKEN:
    updater = bot_types.UpdatersStack(telegram.ext.Updater(token=settings.Telegram.DEV_TOKEN, workers=29))
else:
    updater = bot_types.UpdatersStack(
        telegram.ext.Updater(token=settings.Telegram.TOKEN, workers=29),
        telegram.ext.Updater(token=settings.Telegram.GROUP_TOKEN, workers=29)
    )

chats_input_state = {}
chats_adv_count = {}
chats_inline_count = {}


def should_send_advertisement(chat_settings: bot_types.ChatSettings):
    try:
        if chats_adv_count[chat_settings.id] < 10:
            chats_adv_count[chat_settings.id] += 1
        else:
            chats_adv_count[chat_settings.id] = 1
    except KeyError:
        chats_adv_count[chat_settings.id] = 1

    # each 10th message and if not donated and if ( private chat or not quiet )
    return chats_adv_count[chat_settings.id] == 10 and \
           not chat_settings.donate and \
           (chat_settings.admin_id == chat_settings.id or not chat_settings.quiet)


# region start handlers

def start_message(bot: telegram.Bot, update: telegram.Update, args: list = None):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Command start: init.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    if args and args[0] == 'donate':
        logging.info('Command start: donate', extra={'id': log_id})

        donate_thank_message(bot, update)
    else:
        chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat, admin_id=update.message.from_user.id,
                                               admin_name=update.message.from_user.first_name)

        if not chat_settings.admin_only or chat_settings.admin_id == update.message.from_user.id:
            logging.info('Command start: send start message', extra={'id': log_id})

            send_start_message(bot, update.message.chat_id, chat_settings.tg_name)
            send_settings_message(bot, chat_settings)

            bot_types.Botan.track(
                uid=update.message.chat_id,
                message=update.message.to_dict(),
                name='start'
            )

    logging.info('Command start: end', extra={'id': log_id})


@run_async
def send_start_message(bot: telegram.Bot, chat_id, user_name):
    bot.send_message(
        chat_id=chat_id,
        text=strings.START_MESSAGE % user_name
    )


updater.add_handlers(telegram.ext.CommandHandler('start', start_message, pass_args=True))
updater.add_handlers(extentions.LambdaHandler(
    lambda update: isinstance(update, telegram.Update) and update and update.message and
                   update.message.new_chat_member and
                   (update.message.new_chat_member.id == settings.Telegram.BOT_GROUP_ID or
                    update.message.new_chat_member.id == settings.Telegram.BOT_DEV_ID or
                    update.message.new_chat_member.id == settings.Telegram.BOT_ID),
    start_message
))


# endregion


# region reply command handlers

@run_async
def send_reply_message(bot: telegram.Bot, update: telegram.Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=strings.REPLY_MESSAGE,
        reply_markup=telegram.ForceReply()
    )

updater.add_handlers(telegram.ext.CommandHandler('send', send_reply_message))
updater.add_handlers(telegram.ext.CommandHandler('0', send_reply_message))


# endregion


# region help handlers

@run_async
def help_about(bot: telegram.Bot, update: telegram.Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=strings.HELP_MESSAGE,
        parse_mode='HTML',
        disable_web_page_preview=True,
        reply_markup=strings.HELP_MESSAGE_KEYBOARD
    )

    bot_types.Botan.track(
        uid=update.message.chat_id,
        message=update.message.to_dict(),
        name='help.about'
    )
    logging.info('Command help: about.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    })


@run_async
def help_about_callback(bot: telegram.Bot, update: telegram.Update):
    bot.edit_message_text(
        chat_id=update.callback_query.message.chat.id,
        message_id=update.callback_query.message.message_id,
        text=strings.HELP_MESSAGE,
        parse_mode='HTML',
        disable_web_page_preview=True,
        reply_markup=strings.HELP_MESSAGE_KEYBOARD
    )
    bot.answer_callback_query(
        callback_query_id=update.callback_query.id
    )

    bot_types.Botan.track(
        uid=update.callback_query.message.chat_id,
        message=update.callback_query.message.to_dict(),
        name='help.about'
    )
    logging.info('Command help: about.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.callback_query.message.chat_id,
            'message_id': update.callback_query.message.message_id,
        },
        'id': extentions.TextHelper.get_md5(str(update.callback_query.id))
    })


@run_async
def help_commands_callback(bot: telegram.Bot, update: telegram.Update):
    bot.edit_message_text(
        chat_id=update.callback_query.message.chat.id,
        message_id=update.callback_query.message.message_id,
        text=strings.COMMANDS_MESSAGE,
        parse_mode='HTML',
        disable_web_page_preview=True,
        reply_markup=strings.COMMANDS_MESSAGE_KEYBOARD
    )
    bot.answer_callback_query(
        callback_query_id=update.callback_query.id
    )

    bot_types.Botan.track(
        uid=update.callback_query.message.chat_id,
        message=update.callback_query.message.to_dict(),
        name='help.commands'
    )
    logging.info('Command help: commands.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.callback_query.message.chat_id,
            'message_id': update.callback_query.message.message_id,
        },
        'id': extentions.TextHelper.get_md5(str(update.callback_query.id))
    })


updater.add_handlers(telegram.ext.CommandHandler('help', help_about))
updater.add_handlers(extentions.MyCallbackQueryHandler('h.commands', help_commands_callback))
updater.add_handlers(extentions.MyCallbackQueryHandler('h.about', help_about_callback))


# endregion


# region settings handlers

# region settings main

def settings_message(bot: telegram.Bot, update: telegram.Update):
    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if not chat_settings.admin_only or chat_settings.admin_id == update.message.from_user.id:
        send_settings_message(bot, chat_settings)

    bot_types.Botan.track(
        uid=update.message.chat_id,
        message=update.message.to_dict(),
        name='settings.main'
    )
    logging.info('Command settings: main.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    })


@run_async
def send_settings_message(bot: telegram.Bot, chat_settings: bot_types.ChatSettings):
    bot.send_message(
        chat_id=chat_settings.id,
        text=strings.SETTINGS_MESSAGE % (
            chat_settings.admin_name,
            str(chat_settings.mode),
            'включен' if chat_settings.quiet else 'выключен',
            'только администратор бота' if chat_settings.admin_only else 'кто угодно',
            str(chat_settings.voice),
            str(chat_settings.emotion),
            str(chat_settings.speed),
            'аудиозапись' if chat_settings.as_audio else 'голосовое сообщение',
            'голосовое сообщение' if chat_settings.as_audio else 'аудиозапись',
            'выключить' if chat_settings.quiet else 'включить',
            'любой' if chat_settings.admin_only else 'только администратор бота'
        ),
        parse_mode='HTML'
    )


# endregion


# region settings voice

@run_async
def settings_voice_message(bot: telegram.Bot, update: telegram.Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=strings.SETTINGS_VOICE_CHOOSE_MESSAGE,
        parse_mode='HTML',
        reply_markup=strings.SETTINGS_VOICE_CHOOSE_MESSAGE_KEYBOARD
    )

    bot_types.Botan.track(
        uid=update.message.chat_id,
        message=update.message.to_dict(),
        name='settings.voice.get'
    )
    logging.info('Command settings: voice.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    })


def settings_voice_message_callback(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.callback_query.id))
    logging.info('Command settings: voice begin.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.callback_query.message.chat_id,
            'message_id': update.callback_query.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.callback_query.message.chat)

    if not chat_settings.admin_only or chat_settings.admin_id == update.callback_query.from_user.id:
        voice = extentions.EnumHelper.parse(bot_types.Voice, update.callback_query.data.split('.')[1])

        logging.info('Command settings: voice set.', extra={'id': log_id})

        db.update_one(
            {'_id': chat_settings.id},
            {'$set': {
                'voice': voice.name
            }}
        )
        send_settings_voice_message_callback(bot, voice, update.callback_query.id, chat_settings.quiet)
        bot_types.Botan.track(
            uid=update.callback_query.message.chat_id,
            message=update.callback_query.message.to_dict(),
            name='settings.voice.' + voice.name
        )

    logging.info('Command settings: voice end.', extra={'id': log_id})


@run_async
def send_settings_voice_message_callback(bot: telegram.Bot, voice: bot_types.Voice,
                                         callback_query_id: str, quiet: bool):
    if quiet:
        bot.answer_callback_query(
            callback_query_id=callback_query_id
        )
    else:
        bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text=strings.NEW_VOICE_MESSAGE % str(voice)
        )


# endregion


# region settings emotion

@run_async
def settings_emotion_message(bot: telegram.Bot, update: telegram.Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=strings.SETTINGS_EMOTION_CHOOSE_MESSAGE,
        parse_mode='HTML',
        reply_markup=strings.SETTINGS_EMOTION_CHOOSE_MESSAGE_KEYBOARD
    )

    bot_types.Botan.track(
        uid=update.message.chat_id,
        message=update.message.to_dict(),
        name='settings.emotions.get'
    )
    logging.info('Command settings: emotion.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    })


def settings_emotion_message_callback(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.callback_query.id))
    logging.info('Command settings: emotion begin.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.callback_query.message.chat_id,
            'message_id': update.callback_query.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.callback_query.message.chat)

    if not chat_settings.admin_only or chat_settings.admin_id == update.callback_query.from_user.id:
        emotion = extentions.EnumHelper.parse(bot_types.Emotion, update.callback_query.data.split('.')[1])

        logging.info('Command settings: emotion set.', extra={'id': log_id})

        db.update_one(
            {'_id': chat_settings.id},
            {'$set': {
                'emotion': emotion.name
            }}
        )
        send_settings_emotion_message_callback(bot, emotion, update.callback_query.id, chat_settings.quiet)
        bot_types.Botan.track(
            uid=update.callback_query.message.chat_id,
            message=update.callback_query.message.to_dict(),
            name='settings.emotion.' + emotion.name
        )

    logging.info('Command settings: emotion end.', extra={'id': log_id})


@run_async
def send_settings_emotion_message_callback(bot: telegram.Bot, emotion: bot_types.Emotion,
                                           callback_query_id: str, quiet: bool):
    if quiet:
        bot.answer_callback_query(
            callback_query_id=callback_query_id
        )
    else:
        bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text=strings.NEW_EMOTION_MESSAGE % str(emotion)
        )


# endregion


# region settings mode

@run_async
def settings_mode_message(bot: telegram.Bot, update: telegram.Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text=strings.SETTINGS_MODE_CHOOSE_MESSAGE,
        parse_mode='HTML',
        reply_markup=strings.SETTINGS_MODE_CHOOSE_MESSAGE_KEYBOARD
    )

    bot_types.Botan.track(
        uid=update.message.chat_id,
        message=update.message.to_dict(),
        name='settings.mode.get'
    )
    logging.info('Command settings: mode.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    })


def settings_mode_message_callback(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.callback_query.id))
    logging.info('Command settings: mode begin.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.callback_query.message.chat_id,
            'message_id': update.callback_query.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.callback_query.message.chat)

    if not chat_settings.admin_only or chat_settings.admin_id == update.callback_query.from_user.id:
        mode = extentions.EnumHelper.parse(bot_types.Mode, update.callback_query.data.split('.')[1])

        logging.info('Command settings: mode set.', extra={'id': log_id})

        db.update_one(
            {'_id': chat_settings.id},
            {'$set': {
                'mode': mode.name
            }}
        )
        send_settings_mode_message_callback(bot, mode, update.callback_query.id, chat_settings.quiet)
        bot_types.Botan.track(
            uid=update.callback_query.message.chat_id,
            message=update.callback_query.message.to_dict(),
            name='settings.mode.' + mode.name
        )

    logging.info('Command settings: mode end.', extra={'id': log_id})


@run_async
def send_settings_mode_message_callback(bot: telegram.Bot, mode: bot_types.Mode,
                                        callback_query_id: str, quiet: bool):
    if quiet:
        bot.answer_callback_query(
            callback_query_id=callback_query_id
        )
    else:
        bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text=strings.NEW_MODE_MESSAGE % str(mode)
        )


# endregion


# region settings audio

def settings_audio_message(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Command settings: audio begin.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if not chat_settings.admin_only or chat_settings.admin_id == update.message.from_user.id:
        logging.info('Command settings: audio set.', extra={'id': log_id})

        db.update_one(
            {'_id': chat_settings.id},
            {'$set': {
                'audio': not chat_settings.as_audio
            }}
        )
        if not chat_settings.quiet:
            send_settings_audio_message(bot, chat_settings.id, not chat_settings.as_audio)
        bot_types.Botan.track(
            uid=update.message.chat_id,
            message=update.message.to_dict(),
            name='settings.audio.' + str(not chat_settings.as_audio)
        )

    logging.info('Command settings: audio end.', extra={'id': log_id})


@run_async
def send_settings_audio_message(bot: telegram.Bot, chat_id, as_audio: bool):
    bot.send_message(
        chat_id=chat_id,
        text=strings.AUDIO_SWITCH_MESSAGE % ('аудиозапись' if as_audio else 'голосовое сообщение'),
    )


# endregion


# region settings quiet

def settings_quiet_message(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Command settings: quiet begin.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if not chat_settings.admin_only or chat_settings.admin_id == update.message.from_user.id:
        logging.info('Command settings: quiet set.', extra={'id': log_id})

        db.update_one(
            {'_id': chat_settings.id},
            {'$set': {
                'quiet': not chat_settings.quiet
            }}
        )
        if chat_settings.quiet:
            send_settings_quiet_message(bot, chat_settings.id, not chat_settings.quiet)
        bot_types.Botan.track(
            uid=update.message.chat_id,
            message=update.message.to_dict(),
            name='settings.quiet.' + str(not chat_settings.quiet)
        )

    logging.info('Command settings: quiet end.', extra={'id': log_id})


@run_async
def send_settings_quiet_message(bot: telegram.Bot, chat_id, quiet: bool):
    bot.send_message(
        chat_id=chat_id,
        text=strings.QUIET_SWITCH_MESSAGE % ('включен' if quiet else 'выключен'),
    )


# endregion


# region settings admin

def settings_admin_message(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Command settings: admin begin.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if not chat_settings.admin_only or chat_settings.admin_id == update.message.from_user.id:
        logging.info('Command settings: admin set.', extra={'id': log_id})

        db.update_one(
            {'_id': chat_settings.id},
            {'$set': {
                'admin-only': not chat_settings.admin_only
            }}
        )
        if not chat_settings.quiet:
            send_settings_admin_message(bot, chat_settings.id, not chat_settings.admin_only)
        bot_types.Botan.track(
            uid=update.message.chat_id,
            message=update.message.to_dict(),
            name='settings.admin_only.' + str(not chat_settings.admin_only)
        )

    logging.info('Command settings: admin end.', extra={'id': log_id})


@run_async
def send_settings_admin_message(bot: telegram.Bot, chat_id, admin_only: bool):
    bot.send_message(
        chat_id=chat_id,
        text=strings.ADMIN_ONLY_SWITCH_MESSAGE % ('только администратор бота' if admin_only else 'кто угодно'),
    )


# endregion


# region settings speed

def settings_speed_message(bot: telegram.Bot, update: telegram.Update, args: list = None):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Command settings: speed init.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if not chat_settings.admin_only or chat_settings.admin_id == update.message.from_user.id:
        if args:
            try:
                speed = float(args[0])
                if speed <= 0 or speed > 2:
                    raise ValueError('TTS speed lower or equal to 0 or more than 2.')
            except ValueError as err:
                if not chat_settings.quiet:
                    send_settings_speed_message_arg_error(bot, chat_settings.id)

                bot_types.Botan.track(
                    uid=update.message.chat_id,
                    message=update.message.to_dict(),
                    name='settings.speed.error'
                )
                logging.error('Command settings: speed value error.\n\n' + repr(err), extra={'id': log_id})
            else:
                logging.info('Command settings: speed set.', extra={'id': log_id})

                db.update_one(
                    {'_id': chat_settings.id},
                    {'$set': {
                        'speed': speed
                    }}
                )
                if not chat_settings.quiet:
                    send_settings_speed_message(bot, chat_settings.id, speed)
                bot_types.Botan.track(
                    uid=update.message.chat_id,
                    message=update.message.to_dict(),
                    name='settings.speed.' + str(speed)
                )
        else:
            logging.info('Command settings: speed get arg.', extra={'id': log_id})

            chats_input_state[chat_settings.id] = bot_types.ChatInputState.input_speed
            send_settings_speed_message_arg_get(bot, chat_settings.id)
            bot_types.Botan.track(
                uid=update.message.chat_id,
                message=update.message.to_dict(),
                name='settings.speed.get'
            )

    logging.info('Command settings: speed end.', extra={'id': log_id})


@run_async
def send_settings_speed_message(bot: telegram.Bot, chat_id, speed: float):
    bot.send_message(
        chat_id=chat_id,
        text=strings.NEW_SPEED_MESSAGE % str(speed)
    )


@run_async
def send_settings_speed_message_arg_error(bot: telegram.Bot, chat_id):
    bot.send_message(
        chat_id=chat_id,
        text=strings.NEW_SPEED_ARG_ERROR_MESSAGE,
        parse_mode='HTML'
    )


@run_async
def send_settings_speed_message_arg_get(bot: telegram.Bot, chat_id):
    bot.send_message(
        chat_id=chat_id,
        text=strings.NEW_SPEED_ARG_GET_MESSAGE
    )


def settings_speed_arg_message(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Command settings: speed init.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if not chat_settings.admin_only or chat_settings.admin_id == update.message.from_user.id:
        chats_input_state[chat_settings.id] = bot_types.ChatInputState.normal

        try:
            speed = float(update.message.text)
            if speed <= 0 or speed > 2:
                raise ValueError('TTS speed lower or equal to 0 or more than 2.')
        except ValueError as err:
            if not chat_settings.quiet:
                send_settings_speed_message_arg_error(bot, chat_settings.id)

            bot_types.Botan.track(
                uid=update.message.chat_id,
                message=update.message.to_dict(),
                name='settings.speed.error'
            )
            logging.error('Command settings: speed value error.\n\n' + repr(err), extra={'id': log_id})
        else:
            logging.info('Command settings: speed set.', extra={'id': log_id})

            db.update_one(
                {'_id': chat_settings.id},
                {'$set': {
                    'speed': speed
                }}
            )
            if not chat_settings.quiet:
                send_settings_speed_message(bot, chat_settings.id, speed)
            bot_types.Botan.track(
                uid=update.message.chat_id,
                message=update.message.to_dict(),
                name='settings.speed.' + str(speed)
            )


# endregion

updater.add_handlers(telegram.ext.CommandHandler('settings', settings_message))

updater.add_handlers(telegram.ext.CommandHandler('voice', settings_voice_message))
for v in bot_types.Voice:
    updater.add_handlers(
        extentions.MyCallbackQueryHandler('v.' + v.name, settings_voice_message_callback)
    )

updater.add_handlers(telegram.ext.CommandHandler('emotion', settings_emotion_message))
for e in bot_types.Emotion:
    updater.add_handlers(
        extentions.MyCallbackQueryHandler('e.' + e.name, settings_emotion_message_callback)
    )

updater.add_handlers(telegram.ext.CommandHandler('mode', settings_mode_message))
for m in bot_types.Mode:
    updater.add_handlers(
        extentions.MyCallbackQueryHandler('m.' + m.name, settings_mode_message_callback)
    )

updater.add_handlers(telegram.ext.CommandHandler('audio', settings_audio_message))
updater.add_handlers(telegram.ext.CommandHandler('admin', settings_admin_message))
updater.add_handlers(telegram.ext.CommandHandler('quiet', settings_quiet_message))

updater.add_handlers(telegram.ext.CommandHandler('speed', settings_speed_message, pass_args=True))
updater.add_handlers(extentions.LambdaHandler(
    lambda update: isinstance(update, telegram.Update) and update.message and update.message.text and
                   bot_types.ChatInputState.input_speed == chats_input_state.get(
                       update.message.from_user.id,
                       bot_types.ChatInputState.normal
                   ),
    settings_speed_arg_message
))


# endregion


# region donate handlers

def donate_message(bot: telegram.Bot, update: telegram.Update, args: list = None):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Command donate: init.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })
    
    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if not chat_settings.admin_only or chat_settings.admin_id == update.message.from_user.id:
        if args:
            try:
                donate_sum = int(args[0])
                
                if donate_sum <= 0:
                    raise ValueError('bot_types.Donate sum lower or equal to 0.')
            except ValueError as err:
                if not chat_settings.quiet:
                    send_donate_message_arg_error(bot, chat_settings.id)
                    
                bot_types.Botan.track(
                    uid=update.message.chat_id,
                    message=update.message.to_dict(),
                    name='donate.error'
                )
                logging.error('Command donate: value error.\n\n' + repr(err), extra={'id': log_id})
            else:
                logging.info('Command donate: send donate message.', extra={'id': log_id})

                db.update_one(
                    {'_id': chat_settings.id},
                    {'$set': {
                        'donate': False,
                        'donate-sum': chat_settings.donate_sum + donate_sum
                    }}
                )
                send_donate_message(bot, chat_settings.id, donate_sum)
                
                bot_types.Botan.track(
                    uid=update.message.chat_id,
                    message=update.message.to_dict(),
                    name='donate.' + str(donate_sum)
                )
        else:
            logging.info('Command donate: get arg.', extra={'id': log_id})
            
            chats_input_state[chat_settings.id] = bot_types.ChatInputState.input_donate
            send_donate_message_arg_get(bot, chat_settings.id)
            
            bot_types.Botan.track(
                uid=update.message.chat_id,
                message=update.message.to_dict(),
                name='donate.get'
            )

    logging.info('Command donate: end.', extra={'id': log_id})


@run_async
def send_donate_message(bot: telegram.Bot, chat_id, donate_sum: int):
    bot.send_message(
        chat_id=chat_id,
        text=strings.DONATE_MESSAGE % str(donate_sum),
        parse_mode='HTML',
        reply_markup=strings.DONATE_MESSAGE_KEYBOARD % bot_types.Donate.get_url(donate_sum)
    )


@run_async
def send_donate_message_arg_error(bot: telegram.Bot, chat_id):
    bot.send_message(
        chat_id=chat_id,
        text=strings.DONATE_ARG_ERROR_MESSAGE,
        parse_mode='HTML'
    )


@run_async
def send_donate_message_arg_get(bot: telegram.Bot, chat_id):
    bot.send_message(
        chat_id=chat_id,
        text=strings.DONATE_ARG_GET_MESSAGE
    )


def donate_arg_message(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Command donate: init.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if not chat_settings.admin_only or chat_settings.admin_id == update.message.from_user.id:
        chats_input_state[chat_settings.id] = bot_types.ChatInputState.normal

        try:
            donate_sum = int(update.message.text)

            if donate_sum <= 0:
                raise ValueError('bot_types.Donate sum lower or equal to 0.')
        except ValueError as err:
            if not chat_settings.quiet:
                send_donate_message_arg_error(bot, chat_settings.id)

            bot_types.Botan.track(
                uid=update.message.chat_id,
                message=update.message.to_dict(),
                name='donate.error'
            )
            logging.error('Command donate: value error.\n\n' + repr(err), extra={'id': log_id})
        else:
            logging.info('Command donate: send donate message.', extra={'id': log_id})

            db.update_one(
                {'_id': chat_settings.id},
                {'$set': {
                    'donate': False,
                    'donate-sum': chat_settings.donate_sum + donate_sum
                }}
            )
            send_donate_message(bot, chat_settings.id, donate_sum)

            bot_types.Botan.track(
                uid=update.message.chat_id,
                message=update.message.to_dict(),
                name='donate.' + str(donate_sum)
            )

    logging.info('Command donate: end.', extra={'id': log_id})


def donate_thank_message(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Command donate: init.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if chat_settings.donate_sum > 0:
        logging.info('Command donate: send thank message.', extra={'id': log_id})

        db.update_one(
            {'_id': chat_settings.id},
            {'$set': {
                'donate': True
            }}
        )
        send_donate_thank_message(bot, chat_settings.id)

        bot_types.Botan.track(
            uid=update.message.chat_id,
            message=update.message.to_dict(),
            name='donate.finished'
        )

    logging.info('Command donate: end.', extra={'id': log_id})


@run_async
def send_donate_thank_message(bot: telegram.Bot, chat_id):
    bot.send_message(
        chat_id=chat_id,
        text=strings.DONATE_THANK_MESSAGE,
        parse_mode='HTML'
    )


updater.add_handlers(telegram.ext.CommandHandler('donate', donate_message, pass_args=True))
updater.add_handlers(extentions.LambdaHandler(
    lambda update: isinstance(update, telegram.Update) and update.message and update.message.text and
                   bot_types.ChatInputState.input_donate == chats_input_state.get(
                       update.message.from_user.id,
                       bot_types.ChatInputState.normal
                   ),
    donate_arg_message
))


# endregion


# region url handlers

def url_message(bot: telegram.Bot, update: telegram.Update, args: list = None):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Command url: init.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if args:
        url = args[0]

        send_url_message(bot, chat_settings, url, update.message.message_id, log_id)
        bot_types.Botan.track(
            uid=update.message.chat_id,
            message=update.message.to_dict(),
            name='url.' + url
        )
    else:
        logging.info('Command url: get arg.', extra={'id': log_id})

        chats_input_state[chat_settings.id] = bot_types.ChatInputState.input_url
        send_url_message_arg_get(bot, chat_settings.id)

        bot_types.Botan.track(
            uid=update.message.chat_id,
            message=update.message.to_dict(),
            name='url.get'
        )
        logging.info('Command url: end.', extra={'id': log_id})


@run_async
def send_url_message(bot: telegram.Bot, chat_settings: bot_types.ChatSettings,
                     url: str, request_message_id: int, log_id: str):
    try:
        logging.info('Command url: begin.', extra={'id': log_id})

        url = extentions.UrlHelper.prepare_url(url)

        logging.info('Command url: get page content.', extra={'id': log_id})

        # noinspection PyBroadException
        try:
            url_text, url_title = bot_types.Readability.get_text_from_web_page(url)
        except:
            url_text = None
            url_title = 'Article'

        url_text = extentions.UrlHelper.try_custom_text_from_url(url, url_text)

        if not url_text:
            raise Exception('url_text is None')
        else:
            logging.info('Command url: split to parts.', extra={'id': log_id})

            url_text = extentions.TextHelper.unescape(url_text).encode('utf-8')
            parts = extentions.TextHelper.text_to_parts(url_text)

            logging.info('Command url: synthesize.', extra={'id': log_id})

            l = len(parts)
            i = 0
            errors = 0

            if not chat_settings.quiet:
                progress_message_id = bot.send_message(
                    chat_id=chat_settings.id,
                    text=strings.URL_PROGRESS_MESSAGE % (url, '0.0 %', i, l),
                    parse_mode='HTML'
                ).message_id

            with tempfile.NamedTemporaryFile() as temp_file:
                while i < l and errors < 10:
                    try:
                        content = bot_types.Speech.tts(
                            text=parts[i],
                            chat_settings=chat_settings,
                            convert=False
                        )
                    except Exception as err:
                        if not chat_settings.quiet:
                            bot.edit_message_text(
                                chat_id=chat_settings.id,
                                message_id=progress_message_id,
                                text=strings.URL_PROGRESS_ERROR_MESSAGE % (
                                    url, str(int(i / l * 100)) + '%', i, l,
                                    'Не удалось синтезировать текст.'
                                ),
                                parse_mode='HTML'
                            )
                        logging.error('Command url: synthesizing error.\n\n' + repr(err), extra={'id': log_id})
                        errors += 1
                    else:
                        temp_file.write(content)

                        i += 1

                        if not chat_settings.quiet:
                            bot.edit_message_text(
                                chat_id=chat_settings.id,
                                message_id=progress_message_id,
                                text=strings.URL_PROGRESS_MESSAGE % (
                                    url, str(int(i / l * 100)) + '%', i, l
                                ),
                                parse_mode='HTML'
                            )

                temp_file.seek(0)
                audio_content = temp_file.read()
                temp_file.seek(0)

                logging.info('Command url: send result.', extra={'id': log_id})

                bot.send_audio(
                    chat_id=chat_settings.id,
                    audio=temp_file,
                    duration=bot_types.FfmpegWrap.get_duration(audio_content=audio_content),
                    performer='%s | %s' % (str(chat_settings.voice), str(chat_settings.emotion)),
                    title=url_title,
                    reply_to_message_id=request_message_id
                )
    except Exception as err:
        if not chat_settings.quiet:
            bot.send_message(
                chat_id=chat_settings.id,
                text=strings.URL_ERROR_MESSAGE % url,
                parse_mode='HTML'
            )
        bot_types.Botan.track(
            uid=chat_settings.id,
            message={'url': url},
            name='url.error'
        )
        logging.error('Command url: unknown error.\n\n' + repr(err), extra={'id': log_id})
    else:
        if should_send_advertisement(chat_settings):
            logging.info('Command url: send advertisement.', extra={'id': log_id})

            bot.send_message(
                chat_id=chat_settings.id,
                text=strings.ADVERTISEMENT_MESSAGE % bot_types.Addybot.get_advertisement(chat_settings.id),
                parse_mode='HTML'
            )
        
        logging.info('Command url: end.', extra={'id': log_id})


@run_async
def send_url_message_arg_get(bot: telegram.Bot, chat_id):
    bot.send_message(
        chat_id=chat_id,
        text=strings.URL_ARG_GET_MESSAGE
    )


def url_arg_message(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Command url: init.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    chats_input_state[chat_settings.id] = bot_types.ChatInputState.normal

    send_url_message(
        bot, chat_settings,
        re.findall(settings.WEB_URI_REGEX, update.message.text)[0][0],
        update.message.message_id, log_id
    )
    bot_types.Botan.track(
        uid=update.message.chat_id,
        message=update.message.to_dict(),
        name='url.' + update.message.text
    )


updater.add_handlers(telegram.ext.CommandHandler('url', url_message, pass_args=True))
updater.add_handlers(extentions.LambdaHandler(
    lambda update: isinstance(update, telegram.Update) and update.message and update.message.text and
                   bot_types.ChatInputState.input_url == chats_input_state.get(
                       update.message.from_user.id,
                       bot_types.ChatInputState.normal
                   ),
    url_arg_message
))
updater.add_handlers(telegram.ext.RegexHandler(settings.WEB_URI_REGEX, url_arg_message))


# endregion


# region text handlers

def text_to_speech(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Text to speech: init.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if chat_settings.mode == bot_types.Mode.tts or chat_settings.mode == bot_types.Mode.both:
        text = update.message.text

        if len(extentions.TextHelper.escape(text, safe='').encode('utf-8')) <= settings.Speech.Yandex.TEXT_MAX_LEN:
            send_text_to_speech(bot, chat_settings, text, update.message.message_id, log_id)
            bot_types.Botan.track(
                uid=update.message.chat_id,
                message=update.message.to_dict(),
                name='tts'
            )
        else:
            send_long_text_to_speech(bot, chat_settings, text, update.message.message_id, log_id)
            bot_types.Botan.track(
                uid=update.message.chat_id,
                message=update.message.to_dict(),
                name='tts.long'
            )
    else:
        logging.info('Text to speech: end.', extra={'id': log_id})


@run_async
def send_text_to_speech(bot: telegram.Bot, chat_settings: bot_types.ChatSettings,
                        text: str, request_message_id: int, log_id: str):
    logging.info('Text to speech: short begin.', extra={'id': log_id})

    try:
        with tempfile.NamedTemporaryFile() as temp_file:
            audio_content = bot_types.Speech.tts(text, chat_settings, file_like=temp_file)
            temp_file.seek(0)

            logging.info('Text to speech: short send result.', extra={'id': log_id})
            if chat_settings.as_audio:
                bot.send_audio(
                    chat_id=chat_settings.id,
                    audio=temp_file,
                    duration=bot_types.FfmpegWrap.get_duration(audio_content=audio_content),
                    performer='%s | %s' % (str(chat_settings.voice), str(chat_settings.emotion)),
                    title=str(time()),
                    reply_to_message_id=request_message_id,
                    reply_markup=telegram.ForceReply()
                )
            else:
                bot.send_voice(
                    chat_id=chat_settings.id,
                    voice=temp_file,
                    duration=bot_types.FfmpegWrap.get_duration(audio_content=audio_content),
                    reply_to_message_id=request_message_id,
                    reply_markup=telegram.ForceReply()
                )
    except Exception as err:
        if not chat_settings.quiet:
            bot.send_message(
                chat_id=chat_settings.id,
                text=strings.TTS_ERROR_MESSAGE,
                reply_to_message_id=request_message_id,
                parse_mode='HTML'
            )
        logging.error('Text to speech: short unknown error.\n\n' + repr(err), extra={'id': log_id})
    else:
        if should_send_advertisement(chat_settings):
            logging.info('Text to speech: send advertisement.', extra={'id': log_id})

            bot.send_message(
                chat_id=chat_settings.id,
                text=strings.ADVERTISEMENT_MESSAGE % bot_types.Addybot.get_advertisement(chat_settings.id),
                parse_mode='HTML'
            )

        logging.info('Text to speech: short end.', extra={'id': log_id})


@run_async
def send_long_text_to_speech(bot: telegram.Bot, chat_settings: bot_types.ChatSettings,
                             text: bytes, request_message_id: int, log_id: str):
    try:
        logging.info('Text to speech: long begin.', extra={'id': log_id})

        if isinstance(text, str):
            text = text.encode('utf-8')

        parts = extentions.TextHelper.text_to_parts(text)

        logging.info('Text to speech: long synthesize.', extra={'id': log_id})

        l = len(parts)
        i = 0
        errors = 0

        if not chat_settings.quiet:
            progress_message_id = bot.send_message(
                chat_id=chat_settings.id,
                text=strings.LONG_TEXT_PROGRESS_MESSAGE % ('0.0 %', i, l),
                parse_mode='HTML'
            ).message_id

        with tempfile.NamedTemporaryFile() as temp_file:
            while i < l and errors < 10:
                try:
                    content = bot_types.Speech.tts(
                        text=parts[i],
                        chat_settings=chat_settings,
                        convert=False
                    )
                except Exception as err:
                    if not chat_settings.quiet:
                        bot.edit_message_text(
                            chat_id=chat_settings.id,
                            message_id=progress_message_id,
                            text=strings.LONG_TEXT_PROGRESS_ERROR_MESSAGE % (
                                str(int(i / l * 100)) + '%', i, l,
                                'Не удалось синтезировать текст.'
                            ),
                            parse_mode='HTML'
                        )
                    logging.error('Text to speech: long synthesizing error.\n\n' + repr(err), extra={'id': log_id})
                    errors += 1
                else:
                    temp_file.write(content)
                    i += 1

                    if not chat_settings.quiet:
                        bot.edit_message_text(
                            chat_id=chat_settings.id,
                            message_id=progress_message_id,
                            text=strings.LONG_TEXT_PROGRESS_MESSAGE % (
                                str(int(i / l * 100)) + '%', i, l
                            ),
                            parse_mode='HTML'
                        )

            temp_file.seek(0)
            audio_content = temp_file.read()
            temp_file.seek(0)

            logging.info('Text to speech: long send result.', extra={'id': log_id})

            bot.send_audio(
                chat_id=chat_settings.id,
                audio=temp_file,
                duration=bot_types.FfmpegWrap.get_duration(audio_content=audio_content),
                performer='%s | %s' % (str(chat_settings.voice), str(chat_settings.emotion)),
                title=str(time()),
                reply_to_message_id=request_message_id,
                reply_markup=telegram.ForceReply()
            )
    except Exception as err:
        if not chat_settings.quiet:
            bot.send_message(
                chat_id=chat_settings.id,
                text=strings.TTS_ERROR_MESSAGE,
                reply_to_message_id=request_message_id,
                parse_mode='HTML',
            )
        bot_types.Botan.track(
            uid=chat_settings.id,
            message={'text': text},
            name='tts.long.error'
        )
        logging.error('Text to speech: long unknown error.\n\n' + repr(err), extra={'id': log_id})
    else:
        if should_send_advertisement(chat_settings):
            logging.info('Text to speech: long send advertisement.', extra={'id': log_id})

            bot.send_message(
                chat_id=chat_settings.id,
                text=strings.ADVERTISEMENT_MESSAGE % bot_types.Addybot.get_advertisement(chat_settings.id),
                parse_mode='HTML'
            )

        logging.info('Text to speech: long end.', extra={'id': log_id})


updater.add_handlers(telegram.ext.MessageHandler([telegram.ext.Filters.text], text_to_speech))


# endregion


# region audio handlers

def speech_to_text(bot: telegram.Bot, update: telegram.Update):
    log_id = extentions.TextHelper.get_md5(str(update.message.chat_id) + str(update.message.message_id))
    logging.info('Speech to text: init.', extra={
        'telegram': {
            'update': update.to_dict(),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.message.chat)

    if chat_settings.mode == bot_types.Mode.stt or chat_settings.mode == bot_types.Mode.both:
        if update.message.voice:
            send_speech_to_text(bot, chat_settings, update.message.voice.file_id, update.message.message_id, log_id)
        elif update.message.audio:
            send_speech_to_text(bot, chat_settings, update.message.audio.file_id, update.message.message_id, log_id)

        bot_types.Botan.track(
            uid=update.message.chat_id,
            message=update.message.to_dict(),
            name='stt'
        )
    else:
        logging.info('Speech to text: end.', extra={'id': log_id})


@run_async
def send_speech_to_text(bot: telegram.Bot, chat_settings: bot_types.ChatSettings,
                        file_id: str, request_message_id: int, log_id: str):
    logging.info('Speech to text: begin.', extra={'id': log_id})

    try:
        voice_url = bot.get_file(file_id).file_path
        voice_content = requests.get(voice_url).content

        logging.info('Speech to text: recognize voice.', extra={'id': log_id})

        voice_text = bot_types.Speech.stt(content=voice_content, request_id=file_id)

        logging.info('Speech to text: send result.', extra={'id': log_id})

        bot.send_message(
            chat_id=chat_settings.id,
            text=voice_text,
            reply_to_message_id=request_message_id
        )
    except Exception as err:
        if not chat_settings.quiet:
            bot.send_message(
                chat_id=chat_settings.id,
                text=strings.STT_ERROR_MESSAGE,
                reply_to_message_id=request_message_id,
                parse_mode='HTML'
            )
        logging.error('Speech to text: long unknown error.\n\n' + repr(err), extra={'id': log_id})
    else:
        if should_send_advertisement(chat_settings):
            logging.info('Speech to text: send advertisement.', extra={'id': log_id})

            bot.send_message(
                chat_id=chat_settings.id,
                text=strings.ADVERTISEMENT_MESSAGE % bot_types.Addybot.get_advertisement(chat_settings.id),
                parse_mode='HTML'
            )

        logging.info('Speech to text: end.', extra={'id': log_id})


updater.add_handlers(telegram.ext.MessageHandler(
    [telegram.ext.Filters.voice, telegram.ext.Filters.audio],
    speech_to_text
))


# endregion


# region inline handlers

def inline_query(bot: telegram.Bot, update: telegram.Update):
    log_id = update.inline_query.id
    logging.info('Inline query: init.', extra={
        'telegram': {
            'update': update.to_dict(),
            'from_id': update.inline_query.from_user.id,
        },
        'id': log_id
    })

    chat_settings = bot_types.ChatSettings.from_db(db, update.inline_query.from_user)

    text = update.inline_query.query
    if 0 < len(extentions.TextHelper.escape(text, safe='').encode('utf-8')) <= settings.Speech.Yandex.TEXT_MAX_LEN:
        if (time() - chats_inline_count.get(update.inline_query.from_user.id, 0)) > \
                settings.Telegram.INLINE_WAIT_TIME:
            send_inline_query(bot, chat_settings, text, update.inline_query.id, log_id)
            chats_inline_count[chat_settings.id] = time()
        else:
            send_inline_query_error(
                bot,
                strings.INLINE_WAIT_MESSAGE % settings.Telegram.INLINE_WAIT_TIME,
                update.inline_query.id
            )
            logging.info('Inline query: error too much requests.', extra={'id': log_id})
            logging.info('Inline query: end.', extra={'id': log_id})

        bot_types.Botan.track(
            uid=update.inline_query.from_user.id,
            message=update.inline_query.to_dict(),
            name='inline'
        )
    else:
        send_inline_query_error(
            bot,
            strings.INLINE_BAR_REQUEST_MESSAGE,
            update.inline_query.id
        )
        logging.info('Inline query: error bad request.', extra={'id': log_id})
        logging.info('Inline query: end.', extra={'id': log_id})


@run_async
def send_inline_query(bot: telegram.Bot, chat_settings: bot_types.ChatSettings,
                      text: str, query_id: str, log_id: str):
    logging.info('Inline query: begin.', extra={'id': log_id})

    if isinstance(text, bytes):
        text = text.decode('utf-8')

    url = settings.Telegram.INLINE_URL % (extentions.TextHelper.escape(text, safe=''), chat_settings.id)

    logging.info('Inline query: send link.', extra={'id': log_id})

    if chat_settings.as_audio:
        query_result = telegram.InlineQueryResultAudio(
            id=extentions.TextHelper.get_random_id(),
            audio_url=url,
            performer='%s | %s' % (str(chat_settings.voice), str(chat_settings.emotion)),
            title=text[:15] + '...' if len(text) > 15 else text
            #audio_duration=bot_types.FfmpegWrap.get_duration(audio_content=audio_content)
        )
    else:
        query_result = telegram.InlineQueryResultVoice(
            id=extentions.TextHelper.get_random_id(),
            voice_url=url,
            title=text[:15] + '...' if len(text) > 15 else text
            #voice_duration=bot_types.FfmpegWrap.get_duration(audio_content=audio_content)
        )

    bot.answer_inline_query(
        inline_query_id=query_id,
        is_personal=True,
        cache_time=settings.Telegram.INLINE_CACHE_TIME,
        results=[query_result]
    )

    logging.info('Inline query: end.', extra={'id': log_id})

@run_async
def send_inline_query_error(bot: telegram.Bot, error_text: str, query_id: str):
    bot.answer_inline_query(
        inline_query_id=query_id,
        is_personal=True,
        cache_time=0,
        results=[telegram.InlineQueryResultArticle(
            extentions.TextHelper.get_random_id(),
            'Ошибка',
            telegram.InputTextMessageContent(error_text, parse_mode='HTML'),
            description=error_text
        )]
    )


updater.add_handlers(telegram.ext.InlineQueryHandler(inline_query))

# endregion


updater.start_polling()
updater.idle()
queue_listener.stop()
