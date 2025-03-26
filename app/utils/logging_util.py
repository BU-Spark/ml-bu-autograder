import logging

import colorlog  # Import colorlog for colored logs


def setup_loggers(production=False):
    """Sets up logging with color formatting for console and plain formatting for file."""

    # Colored formatter for console logs
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s[%(asctime)s] %(levelname)s:%(name)s:%(reset)s %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )

    # Plain formatter for file logs (avoid color codes in files)
    file_formatter = logging.Formatter("[%(asctime)s] %(levelname)s:%(name)s: %(message)s")

    # Set log level (DEBUG for dev, INFO for production)
    log_level = logging.INFO if production else logging.DEBUG

    # Create handlers
    file_handler = logging.FileHandler("app.log")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)  # Use plain format for file

    console_handler = colorlog.StreamHandler()  # Use colorlog's handler for colored output
    console_handler.setLevel(log_level)
    console_handler.setFormatter(color_formatter)

    # Get the root logger and add handlers
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.handlers.clear()  # Clear any existing handlers (prevents duplicates)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
