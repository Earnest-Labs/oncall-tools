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
WEEKDAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'] # 0 is monday because python.

def getPagerDutyIncidents(token, since, until, allowedServices,
                          offset = 0, total = True, limit = 100):
    params = { 'since': since.isoformat(),
               'until': until.isoformat(),
               'service_ids[]': allowedServices,
               'offset': offset,
               'limit': limit,
               'total': total }
    headers = headers={'Content-Type': 'application/json',
                       'Accept': 'application/vnd.pagerduty+json;version=2',
                       'Authorization': 'Token token={token}'.format(token=token)}
    r = requests.get(PAGERDUTY_INCIDENTS,params=params,headers=headers)
    r.raise_for_status()
    return r.json()

def getPasswordFromStore(passwordName):
    return subprocess.check_output(['pass', passwordName]).decode('utf-8').strip()

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate

@static_vars(urgencyMap = {'low': 'L', 'high': 'H'})
def mungeIncident(incident):
    createdDateTime = datetime.datetime.fromisoformat(incident['created_at'].replace('Z','+00:00'))
    return { **incident,
             'urgencyCode': mungeIncident.urgencyMap.get(incident['urgency'],'Unknown'),
             'created': { 'date': createdDateTime.date(),
                           'time': createdDateTime.time() },
    }

def groupIncidentsByDate(raw, munger, since, until):
    byDate = {}
    dayCount = (until - since).days +1
    for date in (since.date() + datetime.timedelta(n) for n in range(dayCount)):
        byDate[str(date)] = {'date':date,
                             'weekday':WEEKDAYS[date.weekday()],
                             'incidents':[]}
    for incident in map(munger,raw['incidents']):
        byDate[str(incident['created']['date'])]['incidents'].append(incident)
    return byDate.values()

def readFile(fileName):
    with open(fileName,'r') as f:
        return f.read();

def writeFile(fileName,data):
    with open(fileName,'w') as f:
        f.write(data);

def readYaml(fileName):
    with open(fileName,'r') as f:
        return yaml.load(f)

def timeDeltaFromString(timeSpec):
    t = datetime.datetime.strptime(timeSpec,"%H:%M:%S")
    return datetime.time(hour=t.hour, minute=t.minute, second=t.second)

def timeCurrent(namespace):
    today = datetime.date.today()

    startOfWeek = today + datetime.timedelta(-(today.weekday()+1)) # +1 b/c monday is 0

    since = datetime.datetime.combine(startOfWeek + datetime.timedelta(
        namespace.cutover_weekday), timeDeltaFromString(namespace.cutover_time))

    until = since + datetime.timedelta(7)
    return {'since':since, 'until':until}

def timePrevious(namespace):
    current = timeCurrent(namespace)
    return {'since':current['since'] + datetime.timedelta(-7), 'until':current['until']}

def timeSpan(namespace):
    return {'since':datetime.fromisoformat(namespace.since),
            'until':datetime.fromisoformat(namespace.until)}

def argumentParser(defaults):
    result = argparse.ArgumentParser(description='Generate a weekly on-call report')
    subs = result.add_subparsers(title='subcommands',
                                 description='valid subcommands')

    current = subs.add_parser('current',help='Current week')
    current.set_defaults(func=timeCurrent);

    previous = subs.add_parser('previous',help='Previous week')
    previous.set_defaults(func=timePrevious);

    span = subs.add_parser('span',help='Span of times {-f _timestamp_ -t _timestamp}')
    span.set_defaults(func=timeSpan);
    span.add_argument('-f',dest='since',help='From timestamp',required=True);
    span.add_argument('-t',dest='until',help='To timestamp',required=True);

    result.add_argument('--tz',dest='timezone',help='Timezone')
    result.add_argument('--cutover_weekday',dest='cutover_weekday',type=int,
                        help='Day of week where cutover occurs {Monday=0,Tuesday=1,etc}')
    result.add_argument('--cutover_time',dest='cutover_time',
                        help='Time of day where cutover occurs {e.g., 09:00:00}')
    result.add_argument('--pd-api-token',dest='pd_api_token',
                        help='Pagerduty API token to request using passwordstore.org')
    result.add_argument('--allowed-services',dest='allowed_services',
                        help='Allowed Pagerduty service ids')
    result.add_argument('--template',dest='template',
                        help='Template file name. Uses mustache.io format')
    result.add_argument('-o','--output-file',dest='outputFileName',
                        help='Output file')
    result.add_argument('-e','--edit',dest='edit',action='store_true',default=False,
                        help='Open report in $EDITOR')
    result.add_argument('-c','--copy',dest='copy',action='store_true',default=False,
                        help='Copy report to clipboard')

    result.set_defaults(**defaults)
    return result

def calculateTotal(byDate):
    total = 0
    for date in byDate:
        total = total + len(date['incidents'])
    return total

def hourlyHistogram(byDate):
    hours = [0 for dontCare in range(24)]
    for date in byDate:
        for incident in date['incidents']:
            hour = incident['created']['time'].hour
            hours[hour] = hours[hour] + 1
    return hours

def affectedHours(histogram):
    return sum(x > 0 for x in histogram)

def dayTimePages(histogram):
    return sum(histogram[7:23])

def nightTimePages(histogram):
    return sum(histogram[:7]) + sum(histogram[23:])

def getReportData(args):
    timespan = args.func(args)
    args.since = timespan['since']
    args.until = timespan['until']

    pd_api_token = getPasswordFromStore(args.pd_api_token)
    incidents = getPagerDutyIncidents(pd_api_token, timespan['since'],
                                      timespan['until'], args.allowed_services)

    byDate = groupIncidentsByDate(incidents, mungeIncident,
                                  timespan['since'], timespan['until'])

    histogram = hourlyHistogram(byDate)

    statistics = {
        'total': calculateTotal(byDate),
        'hourlyHistogram': histogram,
        'affectedHours': affectedHours(histogram),
        'dayTimePages': dayTimePages(histogram),
        'nightTimePages': nightTimePages(histogram)
    }

    reportData = {
        'timespan': {'since': timespan['since'].isoformat(), 'until': timespan['until'].isoformat()},
        'incidents': incidents,
        'byDate': byDate,
        'statistics': statistics
    }
    return reportData

def getEditor():
    return os.environ['EDITOR']

def editReport(report):
    tempDir = tempfile.mkdtemp()
    try:
        tempFile = os.path.join(tempDir,'report.md')
        writeFile(tempFile, report)
        subprocess.call([getEditor(),tempFile])
        return readFile(tempFile)
    finally:
        shutil.rmtree(tempDir)

def main():
    defaults = readYaml(CONFIGURATION)
    args = argumentParser(defaults).parse_args()

    reportData = getReportData(args)
    template = readFile(args.template)
    report = pystache.render(template, reportData);
    editedReport = editReport(report)
    if (args.outputFileName):
        writeFile(args.outputFileName, editedReport)
    if (args.copy):
        pyperclip.copy(editedReport) # would be better to upload to confluence.

if __name__=='__main__':
    main()
