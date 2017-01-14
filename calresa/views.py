import os
import json
import datetime
import collections

import flask
from flask import request
from babel import negotiate_locale
import flask_babel
import ics

from .calendar import get_calendar_months
from .state import State
from .roomstate import build_table

AVAILABLE_LOCALES = ['fr', 'en']

app = flask.Flask(__name__)
babel = flask_babel.Babel(app)

def render_template(*args, **kwargs):
    kwargs['url_for_view_prev_month'] = url_for_view_prev_month
    kwargs['url_for_view_next_month'] = url_for_view_next_month
    kwargs['url_for_unselect_date'] = url_for_unselect_date
    kwargs['url_for_select_date'] = url_for_select_date
    resp = flask.make_response(flask.render_template(*args, **kwargs))
    resp.headers['Content-type'] = 'application/xhtml+xml; charset=utf-8'
    return resp

def url_for_view_prev_month():
    state = State.from_request_args(request.args)
    state = state.show_prev_month()
    return flask.url_for('booking_view', **state.to_request_args())

def url_for_view_next_month():
    state = State.from_request_args(request.args)
    state = state.show_next_month()
    return flask.url_for('booking_view', **state.to_request_args())

def url_for_unselect_date(year, month, day):
    state = State.from_request_args(request.args)
    state = state.unselect_date(datetime.date(year, month, day))
    return flask.url_for('booking_view', **state.to_request_args())

def url_for_select_date(year, month, day):
    state = State.from_request_args(request.args)
    state = state.select_date(datetime.date(year, month, day))
    return flask.url_for('booking_view', **state.to_request_args())

@babel.localeselector
def get_locale():
    preferred = [x.replace('-', '_') for x in request.accept_languages.values()]
    return negotiate_locale(preferred, AVAILABLE_LOCALES)

with open('ics/names.json') as fd: # TODO
    rooms = json.load(fd)

_calendar_cache = {} # id -> (last_update, calendar)
def load_calendar(id_):
    global _calendar_cache
    path = 'ics/{}.ics'.format(id_) # TODO
    last_update = os.stat(path).st_mtime
    if id_ not in _calendar_cache or _calendar_cache[id_][0] < last_update:
        with open(path) as fd:
            calendar = ics.Calendar(fd.read())
        _calendar_cache[id_] = (last_update, calendar)
        return calendar
    else:
        return _calendar_cache[id_][1]


@app.route('/')
def booking_view():
    state = State.from_request_args(request.args)
    room_calendars = []
    for room in state.rooms:
        room_calendars.append(load_calendar(room))
    return render_template('booking_view.xhtml',
            rooms=[(n, rooms[str(n)]) for n in state.rooms],
            months=get_calendar_months(state.dates, state.viewed_month),
            selected_dates=state.dates,
            quarterhours=build_table(state.dates, room_calendars),
            )
