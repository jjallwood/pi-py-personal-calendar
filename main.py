#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import os
from sys import platform
from datetime import datetime, timedelta
import requests
import os
import atexit

from PIL import Image, ImageFont, ImageDraw
from font_source_serif_pro import SourceSerifProSemibold
from font_source_sans_pro import SourceSansProSemibold

import msal

# Microsoft Auth Flow borrowed from the sources below
#
# https://www.youtube.com/watch?v=1Jyd7SA-0kI
# https://keathmilligan.net/automate-your-work-with-msgraph-and-python
# https://github.com/AzureAD/microsoft-authentication-library-for-python/blob/dev/sample/device_flow_sample.py

APP_ID = os.environ.get('APP_ID')
SCOPES = ['User.Read', 'Calendars.Read']
MS_GRAPH_URL = "https://graph.microsoft.com/v1.0/"

if APP_ID is None:
    raise Exception('No APP_ID specified')

cache = msal.SerializableTokenCache()
if os.path.exists('token_cache.bin'):
    cache.deserialize(open('token_cache.bin', 'r').read())
atexit.register(lambda: open('token_cache.bin', 'w').write(cache.serialize()) if cache.has_state_changed else None)

app = msal.PublicClientApplication(APP_ID, authority='https://login.microsoftonline.com/consumers/', token_cache=cache)
accounts = app.get_accounts()

result = None
if len(accounts) > 0:
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
if result is None:
    flow = app.initiate_device_flow(scopes=SCOPES)
    if 'user_code' not in flow:
        raise Exception('Failed to create device flow')
    print(flow['message'])
    result = app.acquire_token_by_device_flow(flow)
if 'access_token' in result:
    access_token_id = result['access_token']
else:
    raise Exception('no access token in result')

# Post Auth, Microsoft Calendar API requests
#
# https://learn.microsoft.com/en-us/graph/api/user-list-calendarview?view=graph-rest-1.0

headers = { 'Authorization': 'Bearer ' + access_token_id }

calendarsResponse = requests.get('{base_url}me/calendars?$select=name'.format(base_url=MS_GRAPH_URL), headers=headers)
bjCalendarId = calendarsResponse.json()['value'][1]['id']

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
monthLater = (today + timedelta(days=30))

calendarViewUrl = '{base_url}me/calendars/{calendar_id}/calendarView?$top=100&$select=subject,body,start,end,isAllDay,isCancelled,location&$orderby=start/dateTime&startdatetime={start_date_iso}&enddatetime={end_date_iso}'.format(base_url=MS_GRAPH_URL, calendar_id=bjCalendarId, start_date_iso=today.isoformat(), end_date_iso=monthLater.isoformat())
bjEventsResponse = requests.get(calendarViewUrl, headers=headers)
bjEvents = bjEventsResponse.json()['value']
numberOfEventsToShow = len(bjEvents)
print('Number of events loaded {}'.format(numberOfEventsToShow))

# Inky screen render logic borrowed from the Inky docs
#
# https://github.com/pimoroni/inky

print("Inky wHAT render script")

def reflow_quote(quote, width, font):
    words = quote.split(" ")
    reflowed = '"'
    line_length = 0

    for i in range(len(words)):
        word = words[i] + " "
        word_length = font.getlength(word)
        line_length += word_length

        if line_length < width:
            reflowed += word
        else:
            line_length = word_length
            reflowed = reflowed[:-1] + "\n  " + word

    reflowed = reflowed.rstrip() + '"'

    return reflowed

WIDTH = 400
HEIGHT = 300

if platform == "win32":
    YELLOW = (207, 190, 71)
    WHITE = (255, 255, 255)
    BLACK = (57, 48, 57)
else:
    YELLOW = 2
    WHITE = 0
    BLACK = 1

# Create a new canvas to draw on

img = Image.new("P", (WIDTH, HEIGHT), WHITE)
draw = ImageDraw.Draw(img)

# Load the fonts


font_size = 16
author_font = ImageFont.truetype(SourceSerifProSemibold, font_size)
quote_font = ImageFont.truetype(SourceSansProSemibold, font_size)
screen_padding = 10
listing_padding = 4
day_row_width = author_font.getlength('Thu 000')

last_date = None
for index, event in enumerate(bjEvents):
    draw_height_for_this_event = screen_padding + index * (font_size + listing_padding)

    subject = event['subject']
    is_all_day = event['isAllDay']
    startTime = event['start']['dateTime']
    startTime = startTime[:19]
    dt = datetime.fromisoformat(startTime)
    day_of_the_week = dt.strftime('%a %d')
    if last_date == day_of_the_week:
        draw.rectangle(
            (screen_padding + day_row_width - 10, draw_height_for_this_event + listing_padding, screen_padding + day_row_width - 9, draw_height_for_this_event + font_size),
            fill=BLACK)
    else:
        draw.text((screen_padding + day_row_width - 10, draw_height_for_this_event), day_of_the_week, fill=BLACK, font=quote_font,
                            align="right", anchor="ra")
    last_date = day_of_the_week

    if not is_all_day:
        subject = '{time} - {subject}'.format(time=dt.strftime('%H:%M') ,subject=subject)

    draw.multiline_text((screen_padding + day_row_width, draw_height_for_this_event), subject, fill=BLACK, font=quote_font, align="left")


if platform == "win32":
    img.save("mock-inky-output.png")
else:
    from inky.auto import auto
    inky_display = auto(ask_user=True, verbose=True)
    inky_display.set_border(inky_display.WHITE)

    # inky_display.set_rotation(180)

    inky_display.set_image(img)
    inky_display.show()
