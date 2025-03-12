#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import os
from sys import platform
from datetime import datetime, timedelta
from dateutil import tz
import requests
import os
import atexit
import numpy as np

from PIL import Image, ImageFont, ImageDraw
from font_source_serif_pro import SourceSerifProSemibold

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
fyiCalendarId = calendarsResponse.json()['value'][2]['id']

today = datetime.now().replace(hour=0, minute=1, second=0, microsecond=0)
monthLater = (today + timedelta(days=30))

calendarViewUrl = '{base_url}me/calendars/{calendar_id}/calendarView?$top=100&$select=subject,body,start,end,isAllDay,isCancelled,location&$orderby=start/dateTime&startdatetime={start_date_iso}&enddatetime={end_date_iso}'.format(base_url=MS_GRAPH_URL, calendar_id=bjCalendarId, start_date_iso=today.isoformat(), end_date_iso=monthLater.isoformat())
bjEventsResponse = requests.get(calendarViewUrl, headers=headers)
bjEvents = bjEventsResponse.json()['value']
calendarViewUrl = '{base_url}me/calendars/{calendar_id}/calendarView?$top=100&$select=subject,body,start,end,isAllDay,isCancelled,location&$orderby=start/dateTime&startdatetime={start_date_iso}&enddatetime={end_date_iso}'.format(base_url=MS_GRAPH_URL, calendar_id=fyiCalendarId, start_date_iso=today.isoformat(), end_date_iso=monthLater.isoformat())
fyiEventsResponse = requests.get(calendarViewUrl, headers=headers)
fyiEvents = fyiEventsResponse.json()['value']

bjEvents = np.concatenate((bjEvents, fyiEvents))
bjEvents = sorted(bjEvents, key=lambda event: datetime.fromisoformat(event['start']['dateTime'][:19]))

numberOfEventsToShow = len(bjEvents)
print('Number of events loaded {}'.format(numberOfEventsToShow))

# Inky screen render logic borrowed from the Inky docs
#
# https://github.com/pimoroni/inky

print("Inky wHAT render script")

def reflow_quote(quote, width, font, break_string='...'):
    words = quote.split(" ")
    reflowed = ''
    line_length = 0

    for i in range(len(words)):
        word = words[i] + " "
        word_length = font.getlength(word)
        line_length += word_length

        if line_length < width - font.getlength(break_string):
            reflowed += word
        else:
            return reflowed + break_string

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


font_size = 20
primary_font = ImageFont.truetype(SourceSerifProSemibold, font_size)
screen_padding = 5
listing_padding = 4
day_row_width = max(primary_font.getlength('Thu 00'), primary_font.getlength('Today')) + screen_padding

last_date = None
space_on_screen = True
for index, event in enumerate(bjEvents):
    draw_height_for_this_event = screen_padding + index * (font_size + listing_padding)
    if (draw_height_for_this_event + font_size + screen_padding) > HEIGHT:
        screen_padding = False
        break
    subject = event['subject']
    is_all_day = event['isAllDay']
    startTime = event['start']['dateTime']
    startTime = startTime[:19]
    dt = datetime.fromisoformat(startTime)
    dt = dt.replace(tzinfo=tz.gettz('UTC'))
    dt = dt.astimezone(tz.gettz('Europe/London'))
    if dt.date() == datetime.now().date():
        day_fill = YELLOW
        day_of_the_week = 'Today'
        left, top, right, bottom = primary_font.getbbox(day_of_the_week)
        draw.rectangle(
            (
                0,
                draw_height_for_this_event + (listing_padding / 2),
                screen_padding + right + screen_padding,
                int(draw_height_for_this_event + bottom)
            ),
            fill=YELLOW)
        if last_date != day_of_the_week:
            draw.text((screen_padding + day_row_width - screen_padding, draw_height_for_this_event), day_of_the_week,
                      fill=BLACK, font=primary_font,
                      align="right", anchor="ra")
    else:
        day_of_the_week = dt.strftime('%a %d')
        day_fill = BLACK
        if last_date == day_of_the_week:
            draw.rectangle(
                (screen_padding + day_row_width - screen_padding, draw_height_for_this_event + listing_padding, screen_padding + day_row_width - screen_padding + 1, draw_height_for_this_event + font_size),
                fill=day_fill)
        else:
            draw.text((screen_padding + day_row_width - screen_padding, draw_height_for_this_event), day_of_the_week, fill=day_fill, font=primary_font,
                      align="right", anchor="ra")
    last_date = day_of_the_week

    subject_x = screen_padding + day_row_width
    if not is_all_day:
        time = time=dt.strftime('%H:%M')
        subject_x = subject_x + primary_font.getlength(time) + screen_padding
        draw.text((screen_padding + day_row_width, draw_height_for_this_event), time, fill=YELLOW, font=primary_font, align="left")

    subject_width_available = WIDTH - subject_x - screen_padding
    draw.text((subject_x, draw_height_for_this_event), reflow_quote(subject, subject_width_available, primary_font), fill=BLACK, font=primary_font, align="left")


if platform == "win32":
    img.save("mock-inky-output.png")
else:
    from inky.auto import auto
    inky_display = auto(ask_user=True, verbose=True)
    inky_display.set_border(inky_display.WHITE)

    inky_display.v_flip = True
    inky_display.h_flip = True

    inky_display.set_image(img)
    inky_display.show()
