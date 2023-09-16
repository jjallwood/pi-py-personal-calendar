#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import os
from datetime import datetime, timedelta
import requests
import os
import atexit

from inky.auto import auto

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

# Set up the correct display and scaling factors

inky_display = auto(ask_user=True, verbose=True)
inky_display.set_border(inky_display.WHITE)


# inky_display.set_rotation(180)

# This function will take a quote as a string, a width to fit
# it into, and a font (one that's been loaded) and then reflow
# that quote with newlines to fit into the space required.


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


WIDTH = inky_display.width
HEIGHT = inky_display.height

# Create a new canvas to draw on

img = Image.new("P", (WIDTH, HEIGHT))
draw = ImageDraw.Draw(img)

# Load the fonts

font_size = 24

author_font = ImageFont.truetype(SourceSerifProSemibold, font_size)
quote_font = ImageFont.truetype(SourceSansProSemibold, font_size)

# The amount of padding around the quote. Note that
# a value of 30 means 15 pixels padding left and 15
# pixels padding right.
#
# Also define the max width and height for the quote.

padding = 50
max_width = WIDTH - padding
max_height = HEIGHT - padding - author_font.size

below_max_length = False

# Only pick an event that will fit in our defined area
# once rendered in the font and size defined.

eventIndex = 2
eventDate = 'test'

while not below_max_length:
    event = random.choice(bjEvents)
    subject = event['subject']
    eventDate = event['start']['dateTime']

    reflowed = reflow_quote(subject, max_width, quote_font)
    p_w, p_h = quote_font.getsize(reflowed)  # Width and height of quote
    p_h = p_h * (reflowed.count("\n") + 1)  # Multiply through by number of lines

    if p_h < max_height:
        below_max_length = True  # The quote fits! Break out of the loop.

    else:
        eventIndex = eventIndex + 1
        continue

# x- and y-coordinates for the top left of the quote

quote_x = (WIDTH - max_width) / 2
quote_y = ((HEIGHT - max_height) + (max_height - p_h - author_font.getsize("ABCD ")[1])) / 2

# x- and y-coordinates for the top left of the author

author_x = quote_x
author_y = quote_y + p_h

author = "- " + eventDate

# Draw red rectangles top and bottom to frame quote

draw.rectangle(
    (
        padding / 4,
        padding / 4,
        WIDTH - (padding / 4),
        quote_y - (padding / 4)
    ), fill=inky_display.RED)

draw.rectangle(
    (
        padding / 4,
        author_y + author_font.getsize("ABCD ")[1] + (padding / 4) + 5,
        WIDTH - (padding / 4),
        HEIGHT - (padding / 4)
    ), fill=inky_display.RED)

# Add some white hatching to the red rectangles to make
# it look a bit more interesting

hatch_spacing = 12

for x in range(0, 2 * WIDTH, hatch_spacing):
    draw.line((x, 0, x - WIDTH, HEIGHT), fill=inky_display.WHITE, width=3)

# Write our quote and author to the canvas

draw.multiline_text((quote_x, quote_y), reflowed, fill=inky_display.BLACK, font=quote_font, align="left")
draw.multiline_text((author_x, author_y), author, fill=inky_display.RED, font=author_font, align="left")

print(reflowed + "\n" + author + "\n")

# Display the completed canvas on Inky wHAT

inky_display.set_image(img)
inky_display.show()
