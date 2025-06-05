import logging
from datetime import datetime

from flask import request


class RequestFormatter(logging.Formatter):
    def format(self, record):
        record.remote_addr = request.remote_addr if request else "N/A"
        record.url = request.url if request else "N/A"
        record.method = request.method if request else "N/A"
        record.user_agent = request.user_agent.string if request else "N/A"
        record.time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        record.extra_info_str = ""
        # Handle extra fields dynamically
        if hasattr(record, 'extra_info'):
            record.extra_info_str = f"extra_info : {record.extra_info}"
            # for key, value in record.extra_info.items():
            #     setattr(record, key, value)
        return super().format(record)


def setup_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Define the log format including custom fields
    formatter = RequestFormatter(
        '%(time)s - %(remote_addr)s - %(method)s %(url)s - '
        '%(levelname)s - %(message)s - %(extra_info_str)s - [%(user_agent)s]'
    )

    # Create a file handler
    file_handler = logging.FileHandler('app.log')
    file_handler.setFormatter(formatter)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.handlers.clear()  # Clear existing handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Instantiate the logger
logger = setup_logger()
