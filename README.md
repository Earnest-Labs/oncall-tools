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

To generate a report for the current week, run `make report REPORT_OPTIONS="-e -c current"`

To generate a report for the previous week, run `make report REPORT_OPTIONS="-e -c previous"`

To get help from the reporting tool, run `make report REPORT_OPTIONS="-help"`

# Troubleshooting

We're not aware of any troubleshooting stuff that needs to happen
right now. Hopefully we'll be kind as we go through any issues that
arise and update this doc.
