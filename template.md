# Team: Platform

From:{{timespan.since}}

To:{{timespan.until}}

## Oncall Engineers:

* Triage: _[Triage Engineer]_
* Escalation: _[Escalation Engineer]_

## [Pain Index](https://meetearnest.atlassian.net/wiki/spaces/PLAT/pages/374407255/Earnest+Oncall+Happiness+Stress+Scale):

* Triage: _[Triage Pain Index]_
* Escalation: _[Escalation Pain Index]_

# Incidents:
{{#byDate}}

**{{weekday}} {{date}}**

{{#incidents}}
* ({{urgencyCode}}) [{{created.time}} {{incident_number}} - {{title}}]({{html_url}})
{{/incidents}}
{{^incidents}}
No incidents.
{{/incidents}}
{{/byDate}}

# Statistics:

* Total number of pages: {{statistics.total}}
* Hourly histogram: {{statistics.hourlyHistogram}}
* Total number of hours with pages: {{statistics.affectedHours}}
* Incidents by timeframe:
  {{#statistics.dayTimePages}}
  * day (07:00-23:00): {{statistics.dayTimePages}}
  {{/statistics.dayTimePages}}
  {{#statistics.nightTimePages}}
  * night (07:00-23:00): {{statistics.nightTimePages}}
  {{/statistics.nightTimePages}}
* Hours Worked: _[Total Hours Worked]_
  * _[Person]_: _[Hours]_

# Changes Made:

# Tasks To Do:
