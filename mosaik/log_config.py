import sys
import warnings
from loguru import logger

# Set up Loguru to handle Python warnings
logger.remove()  # Remove default handler
logger.add(
    sink=sys.stderr,  # Console output
    level="WARNING",  # Minimum log level
    format="<green>{time}</green> <level>{level}</level> <cyan>{module}</cyan>: {message}",
)

# Redirect warnings to the logging system instead of sys.stderr
def custom_showwarning(message, category, filename, lineno, file=None, line=None):
    logger.warning(f"{filename}:{lineno}: {category.__name__}: {message}")

warnings.showwarning = custom_showwarning