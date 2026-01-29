"""Centralized logging configuration for FloatTime."""
import logging
import os

# Flag to enable/disable debug logging
# Can be overridden by environment variable FLOATTIME_DEBUG
DEBUG_LOGGING = os.environ.get('FLOATTIME_DEBUG', 'False').lower() == 'true'

def setup_logging():
    """Configure the root logger."""
    level = logging.INFO if DEBUG_LOGGING else logging.WARNING
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

def get_logger(name: str):
    """Get a named logger instance."""
    logger = logging.getLogger(name)
    # Ensure the logger respects the global level if not already set
    if not logger.level:
        logger.setLevel(logging.INFO if DEBUG_LOGGING else logging.WARNING)
    return logger

# Initial setup on module import
setup_logging()

