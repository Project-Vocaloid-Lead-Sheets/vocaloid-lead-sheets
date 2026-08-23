#!/usr/bin/env python

import os
import logging
import tempfile
import pathlib
import requests
import threading

from google.auth.transport.requests import AuthorizedSession
import gspread

import env_config
from typing import Any

import concurrent.futures

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
_logger = logging.getLogger(__name__)

class GDriveSession:
    DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
    MIME_TYPE_DRIVE_FOLDER = "application/vnd.google-apps.folder"

    def __init__(self):
        self._credentials = env_config.get_gdrive_credentials()
        self._local = threading.local()

        self._drive_root_id = env_config.get_env_or_fail("GOOGLE_DRIVE_ID")

    @property
    def _drive_session(self) -> AuthorizedSession:
        if not hasattr(self._local, "session"):
            self._local.session = AuthorizedSession(self._credentials)
        return self._local.session

    def find_all_files_in(self, drive_id: str) -> list[dict]:
        """
        Searches the folder that drive_id point to and returns a list of GDrive metadata dictionaries (one dict per
        file discovered inside of the folder which points to drive_id)

        Args:
            drive_id: Drive ID (hash as supplied from Google Drive APIs or from URL). Must be a folder.

        Returns:
            a list of dictionaries, each of which contains the following contents:
            {
                "id": <GDrive file ID>
                "name": <Name of file>
                "mimeType": <File type>
                "md5Checksum": <File checksum>
                "modifiedTime": Last modified time
            }

            Or an empty list if the folder is empty.
        """
        params = {
            "q": f"'{drive_id}' in parents and trashed=false",
            "pageSize": 1000,
            "fields": "nextPageToken,files(id,name,mimeType,md5Checksum,modifiedTime)",
        }

        files = []
        page_token = None
        while True:
            params["pageToken"] = page_token

            response = self._drive_session.get(GDriveSession.DRIVE_FILES_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            files.extend(payload.get("files", []))

            page_token = payload.get("nextPageToken")
            if not page_token:
                return files

    def find_file(self, drive_id: str, name: str, mime_type: str | None = None) -> dict | None:
        """
        Searches the folder that drive_id point to and returns a GDrive metadata dictionary for a file whose name
        and mime_type matches the arguments.

        Args:
            drive_id: Drive ID (hash as supplied from Google Drive APIs or from URL). Must be a folder.
            name: Name of file to look for inside of target directory
            mime_type: Type of file to look for inside of target directory

        Returns:
            a dictionary which contains the following contents:
            {
                "id": <GDrive file ID>
                "name": <Name of file>
                "md5Checksum": <File checksum>
                "modifiedTime": Last modified time
            }

            Or None if we couldn't find the file.
        """

        query = f"'{drive_id}' in parents and trashed=false and name='{name}'"
        if mime_type:
            query += f" and mimeType='{mime_type}'"
        params = {
            "q": query,
            "pageSize": 1000,
            "fields": "nextPageToken,files(id,name,md5Checksum,modifiedTime)",
        }

        response = self._drive_session.get(GDriveSession.DRIVE_FILES_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        file_result = payload.get("files", None)
        if not file_result:
            return None
        if len(file_result) > 1:
            raise ValueError(f"find_file() returned more than one file - query={params}")
        return file_result[0]


    def find_drive_id_by_dir(self, dir_path: pathlib.Path) -> str:
        """
        Searches for the drive_id which represents the folder which dir_path refers to. The path is absolute, based on
        the root of the drive folder this context works under.

        Args:
            dir_path: Path (in pathlib.Path format) of directory to search

        Returns:
            The google drive ID which points to the directory specified
        """

        drive_id = self._drive_root_id

        path_successful = ["."]
        for part in dir_path.parts:
            escaped_part = part.replace("\\", "\\\\").replace("'", "\\'")
            selected_metadata = self.find_file(drive_id, escaped_part, GDriveSession.MIME_TYPE_DRIVE_FOLDER)

            if not selected_metadata:
                partial_path = os.path.join(*path_successful)
                raise ValueError(
                    f"Drive does not contain '{dir_path}'\n"
                    f"Successfully walked '{partial_path}', but could not find '{part}' next",
                )

            path_successful.append(part)
            drive_id = selected_metadata["id"]

        return drive_id


    def find_files_in_dir(self, dir_path: pathlib.Path) -> list[dict[str, any]]:
        """
        Searches for files which are stored in dir_path, which is based off of the root of the Google Drive.

        Args:
            dir_path: Path (in pathlib.Path format) of directory to search

        Returns:
            a list of Google Drive dictionary metadata (one metadata per file) for each file discovered in the dir_path
            specified, or an empty list if no files are within that directory
        """

        return self.find_all_files_in(self.find_drive_id_by_dir(dir_path))

    def download_file(file_id: str, output_file_path: str) -> bool:
        """
        Download a PDF from Google Drive and save it locally to the output path specified

        Currently this uses an HTTP GET session, so this only works on publicly-viewable drive folders.
        """
        try:
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            _logger.debug(f"Downloading file: {download_url} -> {output_file_path}")

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


    def _discover_walk_files_in_dir(self, file_id: str) -> dict[str, str]:
        confirmed_files = {}

        root_meta = self.get_file_metadata(file_id)
        root_meta["name"] = ""  # Need to strip out root filename, otherwise you create one extra dir in your dl
        frontier = [("", root_meta)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            while frontier:
                folder_nodes = []
                next_frontier = []
                for prefix, meta in frontier:
                    curr_path = os.path.join(prefix, meta["name"])
                    if meta["mimeType"] == GDriveSession.MIME_TYPE_DRIVE_FOLDER:
                        folder_nodes.append((curr_path, meta["id"]))
                    else:
                        meta["relative_path"] = curr_path
                        confirmed_files[meta["id"]] = meta

                futures = {
                    executor.submit(self.find_all_files_in, folder_id): curr_path
                    for curr_path, folder_id in folder_nodes
                }

                for future in concurrent.futures.as_completed(futures):
                    parent_path = futures[future]
                    children_meta = future.result()
                    for child_meta in children_meta:
                        next_frontier.append((parent_path, child_meta))
                frontier = next_frontier

        return confirmed_files


    def download_dir(self, file_id: str, output_file_path: str, mimefilter: list[str] = [], verbose: bool = False) -> bool:
        discovered_files = self._discover_walk_files_in_dir(file_id)
        if mimefilter:
            mimefilter = set(mimefilter)
            discovered_files = {
                dl_path: meta for dl_path, meta in discovered_files.items() if meta["mimeType"] in mimefilter
            }

        os.makedirs(output_file_path, exist_ok=True)
        def download_one(child_file_id: str, child_meta: str) -> bool:
            output_path = os.path.join(output_file_path, child_meta["relative_path"])
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            return GDriveSession.download_file(child_file_id, output_path)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(download_one, file_id, meta): meta for file_id, meta in discovered_files.items()
            }

            success = True

            for future in concurrent.futures.as_completed(futures):
                relative_path = futures[future]["relative_path"]
                try:
                    if not future.result():
                        _logger.error(f"Failed to download: {relative_path}")
                        success = False
                    elif verbose:
                        _logger.info(f"Downloaded: {relative_path}")
                except Exception as exc:
                    print(f"Failed: {relative_path}: {exc}")
                    success = False

        return success

    def get_file_metadata(self, file_id: str) -> dict[str, Any]:
        response = self._drive_session.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"fields": "id,name,mimeType,md5Checksum,modifiedTime", "supportsAllDrives": "true"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()


def main():
    import argparse
    import pprint
    import tabulate
    parser = argparse.ArgumentParser(
        description="Google Drive handle for basic file viewing operations.",
    )

    subparsers = parser.add_subparsers(help='subcommand help')
    parser_list = subparsers.add_parser('list', help='list help')
    parser_list.add_argument("list_path", help="List files in a specific subdirectory of the drive")

    parser_download_file = subparsers.add_parser("download", help="download help")
    parser_download_file.add_argument("download_path_file", help="Path to file in Google Drive")
    parser_download_file.add_argument("-o", "--output", help="Download a file to the local path specified", required=True)

    parser_download_dir = subparsers.add_parser("download_dir", help="download_dir help")
    parser_download_dir.add_argument("download_path_dir", help="Path to file in Google Drive")
    parser_download_dir.add_argument("-o", "--output", help="Download a file to the local path specified", required=True)
    parser_download_dir.add_argument("-m", "--mimetype", help="Filter to only download files of a specific mime type", default="")
    args = vars(parser.parse_args())

    session = GDriveSession()
    if args.get("list_path", None):
        files = session.find_files_in_dir(pathlib.Path(args["list_path"]))
        print(tabulate.tabulate(files))
    elif args.get("download_path_file", None):
        directory = pathlib.Path(os.path.dirname(args["download_path_file"]))
        basename = os.path.basename(args["download_path_file"])

        dir_id = session.find_drive_id_by_dir(directory)
        target_meta = session.find_file(dir_id, basename)

        exit(0 if GDriveSession.download_file(target_meta["id"], args["output"]) else 1)
    elif args.get("download_path_dir", None):
        directory = pathlib.Path(os.path.dirname(args["download_path_dir"]))
        basename = os.path.basename(args["download_path_dir"])

        dir_id = session.find_drive_id_by_dir(directory)
        target_meta = session.find_file(dir_id, basename)
        print(target_meta)

        exit(0 if session.download_dir(target_meta["id"], args["output"], mimefilter=[args["mimetype"]]) else 1)
    else:
        parser.print_help()
        exit(1)

if __name__ == "__main__":
    main()
