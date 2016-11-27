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

HELP_MESSAGE = '''<b>Описание</b>
Бот синтезирует русский текст в речь и распознает голосовые сообщения.
Также есть <a href="https://telegram.org/blog/inline-bots">inline режим</a> и чтение текста с веб-страниц.

<b>Версии</b>
@voiceru_bot - обычная версия, для работы в личных сообщениях и в группах с <a href="https://core.telegram.org/bots#privacy-mode">режимом приватности</a> [получает только команды, сообщения с упоминанием бота и ответы на его сообщения].
@voicerug_bot - версия для групп без <a href="https://core.telegram.org/bots#privacy-mode">режима приватности</a> [получает все сообщения в группе].

<b>Ключ Yandex SpeechKit Cloud</b>
Для использования голосов jane, oksana, alyss, omazh, zahar, ermil и для распознавния речи нужно получить ключ Yandex SpeechKit Cloud и установить его с помощью команды /key:
1. Перейти по адресу https://developer.tech.yandex.ru/keys.
2. Войти или зарегестрировать аккаунт.
3. Нажать "Получить ключ".
4. Ввести имя ключа и выбрать SpeechKit Cloud.
5. Заполнить форму.
6. Скопировать ключ.
    например <code>xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx</code>
7. Отправить его сюда через команду /key.
    <code>/key xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx</code>

<b>Допольнительно</b>
Использует <a href="https://tech.yandex.ru/speechkit/cloud/">Yandex SpeechKit Cloud</a> и <a href="https://www.ivona.com">Ivona Text-to-Speech</a>.
Licensed under: <a href="https://opensource.org/licenses/MIT">The MIT License [MIT]</a>
<a href="https://github.com/just806me/voiceru_bot">View on github</a>
Copyright © 2016 @just806me'''

COMMANDS_MESSAGE = '''<b>Доступные команды:</b>
/settings
Раздел настроек.
 ∙ /voice
    Изменить мой голос.
 ∙ /emotion
    Изменить эмоцию моего голоса.
 ∙ /mode
    Изменить режим работы [текст в речь/речь в текст/текст в речь и речь в текст].
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
 ∙ /key <code>ключ</code>
    Изменить ключ Yandex SpeechKit Cloud.
    Получить ключ можно тут - https://developer.tech.yandex.ru/keys.

/send или /0
Показать интерфейс для ответа [для групп с включеным режимом приватности].

/url <code>ссылка</code>
Прочитать текст с веб-страницы. Поддерживаются новостные записи, заметки, статьи и подобное.
Аргумент - ссылка на веб-страницу с нужной записью.
Например <code>/url https://ru.wikipedia.org/wiki/Telegram_[мессенджер]</code>'''

SETTINGS_MESSAGE = '''<b>Настройки:</b>
Администратор [тот, кто добавил бота]: %s.

Режим работы: %s.
Тихий режим [без служебных сообщений]: %s.
Команды может присылать: %s.
Ключ Yandex SpeechKit Cloud: %s.

Голос: %s.
Эмоция: %s.
Скорость: %s.
Присылать как: %s.

<b>Используй:</b>
/voice - для выбора голоса.
/emotion - для выбора эмоции.
/mode - для выбора режима работы.
/speed <code>0..2</code> - для выбора скорости [например <code>/speed 0.55</code>].
/audio - чтоб присылать как %s.
/quiet - чтоб %s тихий режим.
/admin - чтоб команды мог присылать %s.
/key - чтоб изменить <a herf="https://developer.tech.yandex.ru/keys">ключ Yandex SpeechKit Cloud</a>.'''

SETTINGS_VOICE_CHOOSE_MESSAGE = 'Выбери голос, которым будет синтезирован текст:'

NEW_VOICE_MESSAGE = 'Готово! Установлен голос %s.'

SETTINGS_EMOTION_CHOOSE_MESSAGE = 'Выбери эмоцию, с которой будет синтезирован текст:'

NEW_EMOTION_MESSAGE = 'Готово! Установлена эмоция %s.'

SETTINGS_MODE_CHOOSE_MESSAGE = 'Выбери режим работы:'

NEW_MODE_MESSAGE = 'Готово! Установлен режим %s.'

AUDIO_SWITCH_MESSAGE = 'Готово! Теперь синтезированый текст будет присылаться как %s.'

QUIET_SWITCH_MESSAGE = 'Готово! Тихий режим %s.'

ADMIN_ONLY_SWITCH_MESSAGE = 'Готово! Команды может присылать %s.'

NEW_SPEED_MESSAGE = 'Готово! Установлена скорость %s.'

NEW_SPEED_ARG_ERROR_MESSAGE = '''<b>Ошибка:</b> Неверный аргумент. Требуется число от 0.1 до 2.0.
Пример: <code>/speed 1.25</code>'''

NEW_SPEED_ARG_GET_MESSAGE = 'Укажи желаемую скорость [число от 0 до 2]:'

START_MESSAGE = '''Привет, %s!
Отправь текст на русском языке для его озвучки, или голосовое сообщение для его распознавания.'''

URL_ARG_GET_MESSAGE = 'Укажи ссылку на страницу:'

URL_ERROR_MESSAGE = '''<b>Ошибка:</b> Не найден подходящий текст на странице %s.
<i>Обрати внимание:</i>
 ∙ Поддерживаются новостные записи, заметки, статьи и подобное.
 ∙ Требуется прямая ссылка на запись.
 ∙ Сокращенные ссылки не поддерживаются.'''

URL_PROGRESS_MESSAGE = '''Озвучивание текста с %s.
%s [%s/%s].'''
URL_PROGRESS_ERROR_MESSAGE = '''Озвучивание текста с %s.
%s [%s/%s].

<b>Ошибка:</b> %s.
Повторная попытка...'''


LONG_TEXT_PROGRESS_MESSAGE = '''Озвучивание текста.
%s [%s/%s].'''

LONG_TEXT_PROGRESS_ERROR_MESSAGE = '''Озвучивание текста.
%s [%s/%s].

<b>Ошибка:</b> %s.
Повторная попытка...'''

STT_ERROR_MESSAGE = '<b>Ошибка:</b> Не удалось распознать текст из сообщения.'

TTS_ERROR_MESSAGE = '<b>Ошибка:</b> Не удалось синтезировать текст из сообщения.'

REPLY_MESSAGE = '/send'

INLINE_WAIT_MESSAGE = 'Только один запрос раз в %s секунд! Попробуй позже.'

INLINE_BAD_REQUEST_MESSAGE = 'Неправильный запрос, попробуй еще раз.'

NEW_KEY_MESSAGE = 'Готово! Установлен ключ Yandex SpeechKit Cloud %s.'

NEW_KEY_ARG_GET_MESSAGE = '''Укажи свой ключ Yandex SpeechKit Cloud. Его можно получить по адресу https://developer.tech.yandex.ru/keys.
Подробнее - /help'''

TTS_KEY_ERROR_MESSAGE = '''<b>Ошибка:</b>
Я не могу синтезировать речь, так как для установленого голоса нужен ключ Yandex SpeechKit Cloud. Установи его используя команду /key, иначе выбери голос maxim или tatyana используя команду /voice.
Подробнее - /help'''

STT_KEY_ERROR_MESSAGE = '''<b>Ошибка:</b>
Я не могу распознать текст так как для этого нужен ключ Yandex SpeechKit Cloud. Его можно получить по адресу https://developer.tech.yandex.ru/keys и задать используя команду /key.
Подробнее - /help'''

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
        [
            {'text': 'zahar', 'callback_data': 'v.zahar'},
            {'text': 'ermil', 'callback_data': 'v.ermil'}
        ],
        [
            {'text': 'jane', 'callback_data': 'v.jane'},
            {'text': 'oksana', 'callback_data': 'v.oksana'},
            {'text': 'alyss', 'callback_data': 'v.alyss'},
            {'text': 'omazh', 'callback_data': 'v.omazh'}
        ],
        [
            {'text': 'maxim', 'callback_data': 'v.maxim'},
            {'text': 'tatyana', 'callback_data': 'v.tatyana'}
        ]
    ]
})

SETTINGS_EMOTION_CHOOSE_MESSAGE_KEYBOARD = dumps({
    'inline_keyboard': [
        [
            {'text': 'доброжелательный', 'callback_data': 'e.good'},
            {'text': 'злой', 'callback_data': 'e.evil'}
        ],
        [
            {'text': 'нейтральный', 'callback_data': 'e.neutral'}
        ]
    ]
})

SETTINGS_MODE_CHOOSE_MESSAGE_KEYBOARD = dumps({
    'inline_keyboard': [
        [
            {'text': 'текст в речь и речь в текст', 'callback_data': 'm.both'}
        ],
        [
            {'text': 'речь в текст', 'callback_data': 'm.stt'},
            {'text': 'текст в речь', 'callback_data': 'm.tts'}
        ]
    ]
})

# endregion
