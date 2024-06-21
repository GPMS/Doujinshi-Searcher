from pathlib import Path

from enum import Enum
from functools import total_ordering
from datetime import datetime


@total_ordering
class LogLevel(Enum):
    NORMAL = 1
    WARNING = 2
    ERROR = 3

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


DAY = r"%d"
MONTH = r"%m"
YEAR = r"%Y"
HOUR = r"%H"
MINUTE = r"%M"
SECOND = r"%S"


class Logger():
    started = False
    output_file = None
    current_log_level: LogLevel | None = None
    using_terminal = False

    @classmethod
    def use_terminal(cls):
        cls.using_terminal = True
        cls.current_log_level = LogLevel.NORMAL

    @classmethod
    def start_logger(cls, log_filename: str | None = None):
        cls.using_terminal = False
        if cls.started:
            cls.stop_logger()
        if not log_filename:
            timestamp = datetime.now().strftime(
                f"{DAY}.{MONTH}.{YEAR}-{HOUR}.{MINUTE}.{SECOND}")
            log_filename = f"log-{timestamp}.txt"
        LOGS_DIR = "logs"
        Path(LOGS_DIR).mkdir(exist_ok=True)
        cls.output_file = Path(LOGS_DIR, log_filename).open(
            "w",
            encoding="utf-8")
        cls.current_log_level = LogLevel.NORMAL
        cls.started = True

    @classmethod
    def stop_logger(cls):
        if not cls.output_file or not cls.current_log_level:
            raise (Exception("Logger has not started!"))
        cls.output_file.close()

    @classmethod
    def set_log_level(cls, level: LogLevel):
        if cls.using_terminal:
            cls.current_log_level = level
            return
        if not cls.output_file or not cls.current_log_level:
            raise (Exception("Logger has not started!"))
        cls.current_log_level = level

    @classmethod
    def log(cls, message: str):
        if cls.using_terminal:
            if LogLevel.NORMAL >= cls.current_log_level:
                print(message, end="")
            return
        if not cls.output_file or not cls.current_log_level:
            raise (Exception("Logger has not started!"))
        if LogLevel.NORMAL >= cls.current_log_level:
            cls.output_file.write(message)

    @classmethod
    def log_warn(cls, message: str):
        if cls.using_terminal:
            if LogLevel.WARNING >= cls.current_log_level:
                print(f"WARNING: {message}", end="")
            return
        if not cls.output_file or not cls.current_log_level:
            raise (Exception("Logger has not started!"))
        if LogLevel.WARNING >= cls.current_log_level:
            cls.output_file.write(f"WARNING: {message}")

    @classmethod
    def log_error(cls, message: str):
        if cls.using_terminal:
            if LogLevel.ERROR >= cls.current_log_level:
                print(f"ERROR: {message}", end="")
            return
        if not cls.output_file or not cls.current_log_level:
            raise (Exception("Logger has not started!"))
        if LogLevel.ERROR >= cls.current_log_level:
            cls.output_file.write(f"ERROR: {message}")
