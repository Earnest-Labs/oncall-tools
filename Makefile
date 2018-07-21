VENV=$(shell pwd)/.venv
PIP=pip3
ACTIVATE=source $(VENV)/bin/activate
REPORT_OPTIONS=-e -c current

.PHONY: setup
setup: .setup

force-password-check:
	pkill -HUP gpg-agent

.PHONY: report
report: .setup report.py template.md
	$(ACTIVATE) && python report.py $(REPORT_OPTIONS)

.setup: $(VENV) setup.py Makefile
	$(ACTIVATE) && python --version
	$(ACTIVATE) && python setup.py install
	touch $@

$(VENV): .venv-installed
	virtualenv -p python3 --no-site-packages $(VENV)

clean:
	-rm -rf $(VENV) .setup .venv-installed build dist oncallTools.egg-info

.venv-installed:
	which virtualenv || $(PIP) install virtualenv
	touch $@
