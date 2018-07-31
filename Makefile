VENV=$(shell pwd)/.venv
PIP=pip3
ACTIVATE=source $(VENV)/bin/activate
REPORT_OPTIONS=-e -c current

ifneq ($(shell which virtualenv > /dev/null; echo $$?),0)
$(info )
$(info ERROR: virtualenv is not in your $$PATH. Try running:)
$(info   pip3 install virtualenv && sudo /usr/bin/easy_install virtualenv)
$(info )
$(error virtualenv not in path)
endif 

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

$(VENV):
	virtualenv -p python3 --no-site-packages $(VENV)

clean:
	-rm -rf $(VENV) .setup  build dist oncallTools.egg-info

