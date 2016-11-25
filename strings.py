#!/usr/bin/env python
#
# @voiceru_bot Telegram bot app
# https://telegram.me/voiceru_bot
#
# Copyright [C] 2016
# Leonid Kuznetsov @just806me just806me@gmail.com
#
# This program is licensed under The MIT License [MIT]
# See https://opensource.org/licenses/MIT

import settings
from json import dumps
from telegram import Emoji

# region MESSAGES

HELP_MESSAGE = '''<b>Описание:</b>
Бот синтезирует русский текст в речь. Также есть <a href="https://telegram.org/blog/inline-bots">inline режим</a> и чтение текста с веб-страниц.

<b>Версии:</b>
@voiceru_bot - обычная версия, для работы в личных сообщениях и в группах с <a href="https://core.telegram.org/bots#privacy-mode">режимом приватности</a> [получает только команды, сообщения с упоминанием бота и ответы на его сообщения].
@voicerug_bot - версия для групп без <a href="https://core.telegram.org/bots#privacy-mode">режима приватности</a> [получает все сообщения в группе].

<b>Допольнительно:</b>
Использует <a href="https://www.ivona.com">Ivona Text-to-Speech</a>.
Распознавание речи и синтез речи голосами jane, oksana, alyss, omazh, zahar и ermil больше не доступно в связи с невозможностью продолжать использовать Yandex SpeechKit Cloud. 

Licensed under: <a href="https://opensource.org/licenses/MIT">The MIT License [MIT]</a>
<a href="https://github.com/just806me/voiceru_bot">View on github</a>
Copyright © 2016 @just806me'''

COMMANDS_MESSAGE = '''<b>Доступные команды:</b>
/settings
Раздел настроек.
 ∙ /voice
    Изменить мой голос.
 ∙ /speed <code>число</code>
    Изменить скорость моего голоса.
    Аргумент - число от 0 до 2.
    Например <code>/speed 1.25</code>
 ∙ /audio
    Присылать аудиозаписи вместо голосовых сообщений или наоборот.
 ∙ /quiet
    Включить или выключить тихий режим [без служебных сообщений].
 ∙ /admin
    [Для групп]
    Обрабатывать команды от любого или только от администратора бота в этом чате.

/send или /0
Показать интерфейс для ответа [для групп с включеным режимом приватности].

/url <code>ссылка</code>
Прочитать текст с веб-страницы. Поддерживаются новостные записи, заметки, статьи и подобное.
Аргумент - ссылка на веб-страницу с нужной записью.
Например <code>/url https://ru.wikipedia.org/wiki/Telegram_[мессенджер]</code>'''

SETTINGS_MESSAGE = '''<b>Настройки:</b>
Администратор [тот, кто добавил бота]: %s.

Тихий режим [без служебных сообщений]: %s.
Команды может присылать: %s.

Голос: %s.
Скорость: %s.
Присылать как: %s.

<b>Используй:</b>
/voice - для выбора голоса.
/speed <code>0..2</code> - для выбора скорости [например <code>/speed 0.55</code>].
/audio - чтоб присылать как %s.
/quiet - чтоб %s тихий режим.
/admin - чтоб команды мог присылать %s.'''

SETTINGS_VOICE_CHOOSE_MESSAGE = 'Выбери голос, которым будет синтезирован текст:'

NEW_VOICE_MESSAGE = 'Готово! Установлен голос %s.'

AUDIO_SWITCH_MESSAGE = 'Готово! Теперь синтезированый текст будет присылаться как %s.'

QUIET_SWITCH_MESSAGE = 'Готово! Тихий режим %s.'

ADMIN_ONLY_SWITCH_MESSAGE = 'Готово! Команды может присылать %s.'

NEW_SPEED_MESSAGE = 'Готово! Установлена скорость %s.'

NEW_SPEED_ARG_ERROR_MESSAGE = '''<b>Ошибка:</b> Неверный аргумент. Требуется число от 0.1 до 2.0.
Пример: <code>/speed 1.25</code>'''

NEW_SPEED_ARG_GET_MESSAGE = 'Укажи желаемую скорость [число от 0 до 2]:'

START_MESSAGE = '''Привет, %s!
Чтоб начать, отправь текст на русском языке.'''

URL_ARG_GET_MESSAGE = 'Укажи ссылку на страницу:'

URL_ERROR_MESSAGE = '''<b><Ошибка:</b> Не найден подходящий текст на странице %s.
<i>Обрати внимание:</i>
 ∙ Поддерживаются новостные записи, заметки, статьи и подобное.
 ∙ Требуется прямая ссылка на запись.
 ∙ Сокращенные ссылки не поддерживаются.'''

TTS_ERROR_MESSAGE = '<b>Ошибка:</b> Не удалось синтезировать текст из сообщения.'

REPLY_MESSAGE = '/send'

INLINE_WAIT_MESSAGE = 'Только один запрос раз в %s секунд! Попробуй позже.'

INLINE_BAR_REQUEST_MESSAGE = 'Неправильный запрос, попробуй еще раз.'

# endregion

# region KEYBOARDS

HELP_MESSAGE_KEYBOARD = dumps({
    'inline_keyboard': [
        [
            {'text': 'Доступные команды', 'callback_data': 'h.commands'}
        ],
        [
            {'text': 'Обратная связь', 'url': 'https://telegram.me/%s' % settings.Telegram.ADMIN_USERNAME},
            {'text': 'Оценить', 'url': 'https://telegram.me/storebot?start=voiceru_bot'}
        ]
    ]
})

COMMANDS_MESSAGE_KEYBOARD = dumps({
    'inline_keyboard': [
        [
            {'text': 'Описание', 'callback_data': 'h.about'}
        ],
        [
            {'text': 'Обратная связь', 'url': 'https://telegram.me/%s' % settings.Telegram.ADMIN_USERNAME},
            {'text': 'Оценить', 'url': 'https://telegram.me/storebot?start=voiceru_bot'}
        ]
    ]
})

SETTINGS_VOICE_CHOOSE_MESSAGE_KEYBOARD = dumps({
    'inline_keyboard': [
        [ {'text': 'maxim', 'callback_data': 'v.maxim'} ],
        [ {'text': 'tatyana', 'callback_data': 'v.tatyana'} ]
    ]
})

# endregion
