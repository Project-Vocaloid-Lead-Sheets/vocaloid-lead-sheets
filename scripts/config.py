import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Try to load python-dotenv for .env file support
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ Loaded .env file")
except ImportError:
    logger.warning("python-dotenv not installed, using environment variables only")



def get_env_or_fail(varname: str) -> str:
    """Get an environment variable by name, or throw an exception if it's not available"""
    val = os.environ.get(varname)
    if val is None:
        raise ValueError(f"Missing environment variable {varname}; please add to .env")
    return val