# Simple Productivity Blocker Makefile (v1.3.1 Linux Foundation)

PYTHON = python3
PIP = $(PYTHON) -m pip
APP_NAME = SimpleProductivityBlocker

.PHONY: install setup dev build clean

setup:
	$(PIP) install -r requirements.txt

dev:
	sudo $(PYTHON) main.py

build:
	@echo "Building for Linux..."
	# PyInstaller build command for Linux
	python3 -m PyInstaller --noconfirm --onedir --windowed \
		--add-data "newlogo.png:." \
		--name "$(APP_NAME)" main.py
	@echo "Build complete. Output in dist/$(APP_NAME)"

clean:
	rm -rf build/ dist/ *.spec
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Workspace cleaned."

install:
	@echo "Installer stub for v1.3.1..."
	# In v1.3.1, this will handle .deb creation or systemd service setup
	sudo cp -r dist/$(APP_NAME) /opt/
	sudo ln -sf /opt/$(APP_NAME)/$(APP_NAME) /usr/local/bin/spb
	@echo "Installation complete. Run 'spb' to start."
