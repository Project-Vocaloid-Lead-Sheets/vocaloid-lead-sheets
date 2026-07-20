

import gspread
import logging
import os

from oauth2client.service_account import ServiceAccountCredentials
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Singleton Gspread client
_gspread_client: Optional[gspread.Client] = None


def get_client() -> gspread.Client:
    """Retrieves a singleton GSpread client, creating it first if necessary"""
    global _gspread_client
    if _gspread_client is None:
        _gspread_client = _create_client()
    return _gspread_client


def _create_client() -> gspread.Client:
    """Initialize a GSpread client, using one of multiple available methods"""
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]

        # Try different methods to get service account credentials
        creds = None

        # Method 1: From JSON file path (for .env usage)
        json_file_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON_FILE')
        if json_file_path and os.path.exists(json_file_path):
            logger.info(f"Loading service account from file: {json_file_path}")
            creds = ServiceAccountCredentials.from_json_keyfile_name(json_file_path, scope)

        # Method 2: From JSON content (for GitHub Actions)
        elif os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON'):
            logger.info("Loading service account from JSON content")
            import tempfile
            json_content = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')

            # Write to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                temp_file.write(json_content)
                temp_file_path = temp_file.name

            creds = ServiceAccountCredentials.from_json_keyfile_name(temp_file_path, scope)
            os.unlink(temp_file_path)  # Clean up temp file

        # Method 3: Fallback to default service_account.json
        elif os.path.exists('service_account.json'):
            logger.info("Loading service account from default service_account.json")
            creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)

        else:
            raise ValueError(
                "No service account credentials found. Please set:\n"
                "- GOOGLE_SERVICE_ACCOUNT_JSON_FILE (path to JSON file), or\n"
                "- GOOGLE_SERVICE_ACCOUNT_JSON (JSON content), or\n"
                "- Place service_account.json in the current directory"
            )

        return gspread.authorize(creds)
    except Exception as e:
        logger.error(f"Failed to setup Google Sheets connection: {e}")
        raise


def fetch_worksheet() -> tuple[str, gspread.Worksheet]:
    """Fetch a Worksheet by sheet ID and worksheet name or index"""
    try:

        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID environment variable not set")

        # Try to open the sheet and get specific worksheet
        workbook = get_client().open_by_key(sheet_id)

        # Get worksheet by name or index
        worksheet_name = os.environ.get('GOOGLE_SHEET_WORKSHEET_NAME')
        worksheet_index = os.environ.get('GOOGLE_SHEET_WORKSHEET_INDEX')
        sheet: gspread.Worksheet

        if worksheet_name:
            logger.info(f"Using worksheet by name: '{worksheet_name}'")
            sheet = workbook.worksheet(worksheet_name)
        elif worksheet_index:
            # Convert to 0-based index (user provides 1-based)
            index = int(worksheet_index) - 1
            logger.info(f"Using worksheet by index: {index + 1} ('{workbook.worksheets()[index].title}')")
            sheet = workbook.worksheets()[index]
        else:
            logger.info("Using first worksheet (default)")
            sheet = workbook.sheet1  # Use first worksheet

        logger.info(f"Successfully connected to Google Sheet: {sheet_id}")
        logger.info(f"Active worksheet: '{sheet.title}'")

        return (sheet_id, sheet)

    except Exception as e:
        logger.error(f"Failed to fetch Google Sheets worksheet: {e}")
        raise