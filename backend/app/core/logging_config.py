"""Application logging.

There was no logging configuration at all: the two modules that called
`logging.getLogger` inherited uvicorn's setup, and everything else used bare `print`.
That meant no levels, no timestamps, no module names, and no way to quiet or raise
verbosity per deployment.

`LOG_LEVEL` sets the app's own level (default INFO). Third-party loggers that are
noisy at DEBUG are pinned to WARNING so turning the app to DEBUG stays readable.
"""
import logging
import os
from logging.config import dictConfig

LOG_LEVEL = (os.getenv("LOG_LEVEL") or "INFO").upper()

_NOISY = ("httpx", "httpcore", "urllib3", "openai", "groq", "langchain", "langchain_core")


def configure_logging() -> None:
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {"handlers": ["console"], "level": "WARNING"},
        "loggers": {
            # The application's own tree.
            "app": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
            **{n: {"level": "WARNING"} for n in _NOISY},
        },
    })
    logging.getLogger("app").debug("logging configured at %s", LOG_LEVEL)
