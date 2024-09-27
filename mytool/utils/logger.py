import logging
import sys

def configure_logging(level=logging.INFO):
    """
    Configures the logging settings for the application.

    Parameters:
    - level: The logging level (default is logging.INFO). 
      You can pass other levels such as logging.DEBUG, logging.WARNING, etc.

    This function sets up basic logging for the application by:
    - Specifying the logging level (controls which messages will be shown).
    - Setting the format for log messages, including the timestamp, log level, and message.
    - Directing the log output to `sys.stdout`, so logs will appear in the console.
    """
    logging.basicConfig(
        level=level,  # Set the minimum log level (INFO by default)
        format='%(asctime)s [%(levelname)s] %(message)s',  # Format log messages with timestamp and log level
        handlers=[logging.StreamHandler(sys.stdout)]  # Send the log messages to stdout (console)
    )
