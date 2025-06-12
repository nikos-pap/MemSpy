import logging
from typing import Optional


def create_logger(name: str = 'logger', file_path: Optional[str] = None, console: bool = True, append_mode: bool = True) -> logging.Logger:
	"""
	 Parameters
	    ----------
	    name : str
	        name of the logger
	    file_path : str
	        path to write log
	    console: bool
	    	flag to print logs to console as well
	    append_mode: bool
	    	write mode for file logger
	        
	 Returns
	    -------
	    logging.Logger
	        A logger object.

	"""

	# Create a logger
	logger = logging.getLogger(name)
	logger.setLevel(logging.DEBUG)  # Set the logging level

	# Create a file handler to write logs to a file
	file_handler = logging.FileHandler(file_path if file_path else f'logs/{name}.log', mode='a' if append_mode else 'w', encoding='utf-8', errors='replace')
	file_handler.setLevel(logging.DEBUG)  # Set level for file output

	# Create a formatter to define the log message format
	formatter = logging.Formatter('%(levelname)s (%(asctime)s): %(message)s (Line: %(lineno)d)')

	# Apply the formatter to file handler
	file_handler.setFormatter(formatter)
	# Add file handler to the logger
	logger.addHandler(file_handler)

	# Create a console handler to print logs to the console
	console_handler = logging.StreamHandler()

	# Set level for console output
	if console:
		console_handler.setLevel(logging.DEBUG)
	else:
		console_handler.setLevel(logging.INFO)
	# Apply the formatter to file handler
	console_handler.setFormatter(formatter)
	# Add file handler to the logger
	logger.addHandler(console_handler)

	return logger
