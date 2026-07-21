from gdrive_session import GDriveSession

import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
_logger = logging.getLogger(__name__)

class SongDriveRecord:
    def __init__(self, record: dict[str, any]):
        # NOTE: This intentionally raises exceptions if the record doesn't have everything we need!
        self.title = record["Song Name"]
        self.producer = record["Producer"]

class SongRepoSearch:
    def __init__(self, session: GDriveSession):
        self._session = session

    # [x] need a function to read drive id -> get full list of available songs
    # [x] need a function for song name -> gets you the drive contents for that folder

def main():
    parser = argparse.ArgumentParser(
        description="Discovers and correlates what transposed charts have been uploaded for songs",
    )

    parser.add_argument("-n", "--name", required=False, help="Nane of song to search for charts")

    session = GDriveSession()
    session.list_files("Lead Sheets")


if __name__ == "__main__":
    main()
