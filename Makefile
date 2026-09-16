.PHONY: test install chmod

test:
	python3 -m unittest discover -s tests -v

install:
	./scripts/install-sw-proton.sh

chmod:
	chmod +x scripts/sw-compat-wrapper.sh scripts/install-sw-proton.sh scripts/sw-watchdog.py
