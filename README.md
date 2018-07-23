# Oncall Tools

This repository is intended to include tools to aid in running a successful
on-call rotation.

# Dependencies

* python 3.6 or better
* gnu make
* [Pass, the standard unix password manager](http://www.passwordstore.org/)
  * Note: by the transitive property, this implies you need gpg.

# Installation

Assuming you have all the dependencies working, it's fairly straightforward:

```
make setup
```

# Tools

## Weekly Incident Reports

To generate a report for the current week, run `make report
REPORT_OPTIONS="-e -c -o some-file.md current"`. `-e` means "invoke
$EDITOR after generating the report to fill in the blanks locally."
`-c` means "copy the report to the clipboard so it can be pasted into
confluence" `-o {filename}` means "save it to the specified file,
too". Finally, `current` means "run the report for the current week."

To generate a report for the previous week, run `make report
REPORT_OPTIONS="-e -c -o some-file.md previous"`

To get help from the reporting tool, run `make report
REPORT_OPTIONS="-help"`

The reporting tool code is in `report.py`.

It looks for configuration in `~/.etc/oncall-tools.conf.yaml`. All of
the settings in that file are overrideable by command line
options. See `report.py#argumentParser()` for the most recent list of
settings.  The config yaml, as well as the pagerduty api token, are
intentionally left out of this repository.

# Troubleshooting

We're not aware of any troubleshooting stuff that needs to happen
right now. Hopefully we'll be kind as we go through any issues that
arise and update this doc.
