import os
import logging

from google.oauth2.service_account import Credentials

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
_logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
    _logger.info("Loaded .env file")
except ImportError:
    _logger.info("python-dotenv not installed, using environment variables only")

CREDENTIAL_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

def get_env_or_fail(varname: str) -> str:
    """Get an environment variable by name, or throw an exception if it's not available"""
    val = os.environ.get(varname)
    if val is None:
        raise ValueError(f"Missing environment variable {varname}; please add to .env")
    return val

def get_gdrive_credentials() -> Credentials:
    credential_path = "service_account.json"
    temp_file_path = None

    json_file_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_FILE")
    if json_file_path and os.path.exists(json_file_path):
        _logger.info(f"Loading service account from file: {json_file_path}")
        credential_path = json_file_path
    elif json_content := os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        _logger.info("Loading service account from JSON content")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write(json_content)
            temp_file_path = temp_file.name
            credential_path = temp_file_path
    elif os.path.exists(credential_path):
        _logger.info(f"No environment service account JSONs exist - default to {credential_path}")
    else:
        raise ValueError(
            "No service account credentials found. Please set:\n"
            "- GOOGLE_SERVICE_ACCOUNT_JSON_FILE (path to JSON file), or\n"
            "- GOOGLE_SERVICE_ACCOUNT_JSON (JSON content), or\n"
            "- Place service_account.json in the current directory"
        )

    credentials = Credentials.from_service_account_file(
        credential_path,
        scopes=CREDENTIAL_SCOPES
    )

    if temp_file_path:
        os.unlink(temp_file_path)

    return credentials
