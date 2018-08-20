#!/usr/local/bin/python3
import argparse
import datetime
import os
import pyperclip
import pystache
import requests
import shutil
import subprocess
import sys
import tempfile
import urllib
import yaml

PAGERDUTY_ENDPOINT = 'https://api.pagerduty.com/'
PAGERDUTY_INCIDENTS = PAGERDUTY_ENDPOINT + 'incidents'
CONFIGURATION = os.path.expanduser('~/.etc/oncall-tools.conf.yaml')
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] # 0 is monday because python.

def get_pagerduty_incidents(token, since, until, allowed_services,
                          offset = 0, total = True, limit = 100):
    params = { 'since': since.isoformat(),
               'until': until.isoformat(),
               'service_ids[]': allowed_services,
               'offset': offset,
               'limit': limit,
               'total': total }
    headers = headers={'Content-Type': 'application/json',
                       'Accept': 'application/vnd.pagerduty+json;version=2',
                       'Authorization': 'Token token={token}'.format(token=token)}
    r = requests.get(PAGERDUTY_INCIDENTS, params=params, headers=headers)
    r.raise_for_status()
    return r.json()

def get_password_from_store(password_name):
    return subprocess.check_output(['pass', password_name]).decode('utf-8').strip()

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate

@static_vars(urgency_map = {'low': 'L', 'high': 'H'})
def munge_incident(incident):
    """
    Munge the given incident into a format that's more reporting friendly.
    Specifically, convert incident['urgency'] into H/L/Unknown, and
    split up incident['created_at'].
    """
    created_date_time = datetime.datetime.fromisoformat(
        incident['created_at'].replace('Z', '+00:00'))

    return {**incident,
            'urgencyCode': munge_incident.urgency_map.get(incident['urgency'],
                                                          'Unknown'),
            'created': {
                'date': created_date_time.date(),
                'time': created_date_time.time()
            },
    }

def group_incidents_by_date(raw, munger, since, until):
    by_date = {}
    day_count = (until - since).days + 1
    for date in (since.date() + datetime.timedelta(n) for n in range(day_count)):
        by_date[str(date)] = {
            'date':date,
            'weekday':WEEKDAYS[date.weekday()],
            'incidents':[]
        }
    for incident in map(munger, raw['incidents']):
        by_date[str(incident['created']['date'])]['incidents'].append(incident)
    return by_date.values()

def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()

def write_file(filename, data):
    with open(filename, 'w') as f:
        f.write(data)

def read_yaml(filename):
    with open(filename, 'r') as f:
        return yaml.load(f)

def read_defaults(filename):
    try:
        return read_yaml(filename)
    except FileNotFoundError: # don't care
        return {}

def time_from_string(time_spec):
    t = datetime.datetime.strptime(time_spec, "%H:%M:%S")
    return datetime.time(hour=t.hour, minute=t.minute, second=t.second)

def timespan_current(namespace):
    today = datetime.date.today()

    # +1 b/c monday is 0
    start_of_week = today + datetime.timedelta(-(today.weekday()+1))

    since = datetime.datetime.combine(start_of_week + datetime.timedelta(
        namespace.cutover_weekday), time_from_string(namespace.cutover_time))

    until = since + datetime.timedelta(7)
    return {'since':since, 'until':until}

def timespan_previous(namespace):
    current = timespan_current(namespace)
    return {'since':current['since'] + datetime.timedelta(-7),
            'until':current['until'] + datetime.timedelta(-7)}

def timespan(namespace):
    return {'since':datetime.datetime.fromisoformat(namespace.since),
            'until':datetime.datetime.fromisoformat(namespace.until)}

def argument_parser(defaults):
    result = argparse.ArgumentParser(description='Generate a weekly on-call report')
    subs = result.add_subparsers(title='subcommands',
                                 description='valid subcommands')

    current = subs.add_parser('current', help='Current week')
    current.set_defaults(func=timespan_current)

    previous = subs.add_parser('previous', help='Previous week')
    previous.set_defaults(func=timespan_previous)

    span = subs.add_parser('span', help='Span of times {-f _timestamp_ -t _timestamp}')
    span.set_defaults(func=timespan)
    span.add_argument('-f', dest='since', help='From timestamp', required=True)
    span.add_argument('-t', dest='until', help='To timestamp', required=True)

    result.add_argument('--tz', dest='timezone', help='Timezone')
    result.add_argument('--cutover_weekday', dest='cutover_weekday', default=0, type=int,
                        help='Day of week where cutover occurs {Monday=0, Tuesday=1, etc}')
    result.add_argument('--cutover_time', dest='cutover_time', default='09:00:00',
                        help='Time of day where cutover occurs {e.g., 09:00:00}')
    result.add_argument('--pd-api-token', dest='pd_api_token', default='pagerduty_api_token',
                        help='Pagerduty API token to request using passwordstore.org')
    result.add_argument('--allowed-services', dest='allowed_services',
                        help='Allowed Pagerduty service ids')
    result.add_argument('--template', dest='template', default='template.md',
                        help='Template file name. Uses mustache.io format')
    result.add_argument('-o', '--output-file', dest='output_filename',
                        help='Output file')
    result.add_argument('-e', '--edit', dest='edit', action='store_true', default=False,
                        help='Open report in $EDITOR')
    result.add_argument('-c', '--copy', dest='copy', action='store_true', default=False,
                        help='Copy report to clipboard')

    result.set_defaults(**defaults)
    return result

def total_incidents(by_date):
    total = 0
    for date in by_date:
        total = total + len(date['incidents'])
    return total

def hourly_histogram(by_date):
    hours = [0] * 24
    for date in by_date:
        for incident in date['incidents']:
            hour = incident['created']['time'].hour
            hours[hour] = hours[hour] + 1
    return hours

def affected_hours(histogram):
    return sum(x > 0 for x in histogram)

def daytime_pages(histogram):
    return sum(histogram[7:23])

def nighttime_pages(histogram):
    return sum(histogram[:7]) + sum(histogram[23:])

def get_report_data(args):
    timespan = args.func(args)
    args.since = timespan['since']
    args.until = timespan['until']

    pd_api_token = get_password_from_store(args.pd_api_token)
    incidents = get_pagerduty_incidents(pd_api_token, timespan['since'],
                                        timespan['until'], args.allowed_services)

    by_date = group_incidents_by_date(incidents, munge_incident,
                                      timespan['since'], timespan['until'])

    histogram = hourly_histogram(by_date)

    statistics = {
        'total': total_incidents(by_date),
        'hourlyHistogram': histogram,
        'affectedHours': affected_hours(histogram),
        'dayTimePages': daytime_pages(histogram),
        'nightTimePages': nighttime_pages(histogram)
    }

    return {
        'timespan': {
            'since': timespan['since'].isoformat(),
            'until': timespan['until'].isoformat()
        },
        'incidents': incidents,
        'byDate': by_date,
        'statistics': statistics
    }

def get_editor():
    return os.environ['EDITOR']

def edit_report(report):
    temp_dir = tempfile.mkdtemp()
    try:
        temp_file = os.path.join(temp_dir, 'report.md')
        write_file(temp_file, report)
        subprocess.call([get_editor(), temp_file])
        return read_file(temp_file)
    finally:
        shutil.rmtree(temp_dir)

def main():
    defaults = read_defaults(CONFIGURATION)
    args = argument_parser(defaults).parse_args()

    report_data = get_report_data(args)
    template = read_file(args.template)
    report = pystache.render(template, report_data)
    edited_report = edit_report(report)
    if (args.output_filename):
        write_file(args.output_filename, edited_report)
    if (args.copy):
        pyperclip.copy(edited_report) # would be better to upload to confluence.

if __name__=='__main__':
    main()
