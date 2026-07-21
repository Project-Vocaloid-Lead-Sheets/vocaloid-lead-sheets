

import gspread
import logging
import os
import requests

from pathlib import Path

from oauth2client.service_account import ServiceAccountCredentials
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# TODO: move to some common "config" file
def _get_env_or_fail(varname: str) -> str:
    val = os.environ.get(varname)
    if val is None:
        raise ValueError(f"Missing environment variable {varname}; please add to .env")
    return val


GOOGLE_DRIVE_LEAD_SHEETS_FOLDER_ID = _get_env_or_fail("GOOGLE_DRIVE_LEAD_SHEETS_FOLDER_ID")


def _fetch_creds(scopes: list[str]) -> ServiceAccountCredentials:
    """Fetch service account credentials, using one of multiple available methods"""
    # Try different methods to get service account credentials

    # Method 1: From JSON file path (for .env usage)
    json_file_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON_FILE')
    if json_file_path and os.path.exists(json_file_path):
        logger.info(f"Loading service account from file: {json_file_path}")
        return ServiceAccountCredentials.from_json_keyfile_name(json_file_path, scopes)

    # Method 2: From JSON content (for GitHub Actions)
    elif (json_content := os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')):
        logger.info("Loading service account from JSON content")
        import tempfile

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as temp_file:
            temp_file.write(json_content)
            temp_file_path = temp_file.name
            return ServiceAccountCredentials.from_json_keyfile_name(temp_file_path, scopes)

    # Method 3: Fallback to default service_account.json
    elif os.path.exists('service_account.json'):
        logger.info("Loading service account from default service_account.json")
        return ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scopes)

    else:
        raise ValueError(
            "No service account credentials found. Please set:\n"
            "- GOOGLE_SERVICE_ACCOUNT_JSON_FILE (path to JSON file), or\n"
            "- GOOGLE_SERVICE_ACCOUNT_JSON (JSON content), or\n"
            "- Place service_account.json in the current directory"
        )


class GSheetsClient:

    SCOPES = [
                'https://spreadsheets.google.com/feeds',
            ]

    def __init__(self):
        self.client = self._create_client(self.SCOPES)


    def _create_client(self, scopes: list[str]) -> gspread.Client:
        """Initialize a GSpread client, using one of multiple available methods"""
        try:
            return gspread.authorize(_fetch_creds(scopes))
        except Exception as e:
            logger.error(f"Failed to setup Google Sheets connection: {e}")
            raise


    def fetch_worksheet(self) -> tuple[str, gspread.Worksheet]:
        """Fetch a Worksheet by sheet ID and worksheet name or index"""
        try:

            sheet_id = os.environ.get('GOOGLE_SHEET_ID')
            if not sheet_id:
                raise ValueError("GOOGLE_SHEET_ID environment variable not set")

            # Try to open the sheet and get specific worksheet
            workbook = self.client.open_by_key(sheet_id)

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


class GDriveClient:

    SCOPES = [
                'https://www.googleapis.com/auth/drive',
            ]

    def __init__(self):
        pass


    def download_pdf(self, file_id: str, output_filepath: Path) -> bool:
        """Download a PDF from Google Drive and save it locally"""
        try:
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

            logger.info(f"Downloading PDF from Google Drive: {file_id}")

            # Make request with session to handle redirects
            session = requests.Session()
            response = session.get(download_url, stream=True)

            # Handle large file download confirmation
            if 'text/html' in response.headers.get('Content-Type', ''):
                # Look for download confirmation token
                for key, value in response.cookies.items():
                    if key.startswith('download_warning'):
                        params = {'id': file_id, 'confirm': value}
                        response = session.get(download_url, params=params, stream=True)
                        break

            response.raise_for_status()

            # Save to file (create subdirectory if needed)
            os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
            with open(output_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = os.path.getsize(output_filepath)
            logger.info(f"Successfully downloaded PDF: {output_filepath} ({file_size} bytes)")
            return True

        except Exception as e:
            logger.error(f"Failed to download PDF {file_id}: {e}")
            return False


sheets = GSheetsClient()

drive = GDriveClient()
