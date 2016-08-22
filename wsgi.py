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

def application(environ, start_response):
    ctype = 'text/plain'
    response_body = ''
    status = '500 INTERNAL SERVER ERROR'
    
    if environ['PATH_INFO'] == '/':
        status = '200 OK'
        response_body = 'Working ok.'
    
    response_body = response_body.encode('utf-8')
    response_headers = [('Content-Type', ctype), ('Content-Length', str(len(response_body)))]
    start_response(status, response_headers)
    
    return [ response_body ]
#