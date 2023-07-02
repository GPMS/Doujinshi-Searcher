@echo off
copy config-backup.json config.json
python "src/main.py"
