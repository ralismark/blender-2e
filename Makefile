.PHONY: all sync restart reload stop flogs log

all: sync restart

sync:
	rsync -avrh . veno:/home/tim/blender --exclude-from .gitignore
	ssh veno sudo systemctl daemon-reload

restart:
	ssh veno sudo systemctl restart blender

reload:
	ssh veno sudo systemctl reload blender

stop:
	ssh veno sudo systemctl stop blender

flogs:
	ssh veno journalctl -o cat -xafu blender

log:
	ssh veno journalctl -o cat -xau blender
