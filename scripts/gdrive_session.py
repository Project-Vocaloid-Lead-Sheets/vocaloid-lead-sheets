#!/usr/bin/env python

import os
import logging
import tempfile
import pathlib
import requests

from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession
import gspread

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

class GDriveSession:
    DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    MIME_TYPE_DRIVE_FOLDER = "application/vnd.google-apps.folder"

    def __init__(self):
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
        elif os.path.exists("service_account.json"):
            _logger.info("No environment service account JSONs exist - default to service_account.json")
        else:
            raise ValueError(
                "No service account credentials found. Please set:\n"
                "- GOOGLE_SERVICE_ACCOUNT_JSON_FILE (path to JSON file), or\n"
                "- GOOGLE_SERVICE_ACCOUNT_JSON (JSON content), or\n"
                "- Place service_account.json in the current directory"
            )

        credentials = Credentials.from_service_account_file(
            credential_path,
            scopes=GDriveSession.SCOPES,
        )

        self._sheet_client = gspread.authorize(credentials)
        self._drive_session = AuthorizedSession(credentials)

        self._drive_root_id = os.environ.get("GOOGLE_DRIVE_ID")
        if not self._drive_root_id:
            raise ValueError(
                "No root drive ID detected. Please set GOOGLE_DRIVE_ID to the drive folder root we're using.\n"
                "You can extract the ID from the drive URL: https://drive.google.com/drive/folders/{GOOGLE_DRIVE_ID}\n"
                "Example: https://drive.google.com/drive/folders/1SOXrZuHqaj_JLTEEjUCsM5YBnqhARUhi\n"
                " -> set GOOGLE_DRIVE_ID=1SOXrZuHqaj_JLTEEjUCsM5YBnqhARUhi"
            )

        if temp_file_path:
            os.unlink(temp_file_path)

    def _list_files_from_drive_id(self, drive_id: str) -> list[dict]:
        files = []
        page_token = None
        while True:
            params = {
                "q": f"'{drive_id}' in parents and trashed=false",
                "pageSize": 1000,
                "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime)",
            }

            if page_token:
                params["pageToken"] = page_token

            response = self._drive_session.get(GDriveSession.DRIVE_FILES_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            files.extend(payload.get("files", []))

            page_token = payload.get("nextPageToken")
            if not page_token:
                return files

    def list_files(self, directory: str) -> list[dict[str, any]]:
        _logger.info(directory)
        dir_path = pathlib.Path(directory)
        drive_id = self._drive_root_id

        walk_current = self._list_files_from_drive_id(drive_id)
        path_successful = ["."]
        for part in dir_path.parts:
            selected_metadata = None
            for file_metadata in walk_current:
                if file_metadata["name"] == part:
                    selected_metadata = file_metadata
                    break

            if not selected_metadata or selected_metadata["mimeType"] != GDriveSession.MIME_TYPE_DRIVE_FOLDER:
                partial_path = os.path.join(*path_successful)
                raise ValueError(
                    f"Drive does not contain '{directory}'\n"
                    f"Successfully walked '{partial_path}', but could not find '{part}' next",
                )
            path_successful.append(part)
            walk_current = self._list_files_from_drive_id(selected_metadata["id"])

        return walk_current

    def get_metadata(self, drive_id: str) -> dict[str, any]:
        response = self._drive_session.get(
            f"https://www.googleapis.com/drive/v3/files/{drive_id}",
            params={
                "fields": "id,name,mimeType,size,modifiedTime",
            },
        )
        response.raise_for_status()
        return response.json()

    def download_file(file_id: str, output_file_path: str) -> bool:
        """
        Download a PDF from Google Drive and save it locally to the output path specified

        Currently this uses an HTTP GET session, so this only works on publicly-viewable drive folders.
        """
        try:
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            _logger.info(f"Downloading file: {download_url} -> {output_file_path}")

            session = requests.Session()
            response = session.get(download_url, stream=True)
            if 'text/html' in response.headers.get('Content-Type', ''):
                for key, value in response.cookies.items():
                    if key.startswith('download_warning'):
                        params = {'id': file_id, 'confirm': value}
                        response = session.get(download_url, params=params, stream=True)
                        break

            response.raise_for_status()

            # Save download to file (create subdirectory if needed)
            directory = os.path.dirname(output_file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            with open(output_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = os.path.getsize(output_file_path)
            _logger.info(f"Downloaded file: {output_file_path} ({file_size}B)")
            return True

        except Exception as e:
            _logger.error(f"Download failed ({file_id}): {e}")
            return False

def main():
    import argparse
    import pprint
    import tabulate
    parser = argparse.ArgumentParser(
        description="Google Drive handle for basic file viewing operations.",
    )

    parser.add_argument("-l", "--list", help="List files in a specific subdirectory of the drive")
    parser.add_argument("-d", "--download", help="Download a file to the directory specified", nargs="+")
    args = vars(parser.parse_args())

    session = GDriveSession()
    if args["list"]:
        files = session.list_files(args["list"])
        print(tabulate.tabulate(files))
    elif args["download"]:
        if len(args["download"]) != 2:
            print("Download usage: python3 scripts/gdrive_session.py -d /gdrive/remote/path /path/to/local.ext")
            print("Example: python3 scripts/gdrive_session.py -d 'Lead Sheets/wowaka - Rolling Girl/wowaka - Rolling Girl-C.pdf ' /./RollingGirl.pdf")
            exit(1)

        directory = os.path.dirname(args["download"][0])
        basename = os.path.basename(args["download"][0])
        download_path = args["download"][1]

        files = session.list_files(directory)
        for file_metadata in files:
            if file_metadata["name"] == basename:
                _logger.info(f"File selected: {file_metadata}")
                GDriveSession.download_file(file_metadata["id"], download_path)
                exit(0)
        print(f"Could not find file '{args['download'][0]}' to download")

    else:
        parser.print_help()
        exit(1)

if __name__ == "__main__":
    main()
