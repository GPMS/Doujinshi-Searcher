@echo off
@REM copy config.json config-backup.json
@REM xcopy output output-backup /E /H /C /R /Q /Y
python "src/main.py" %*
