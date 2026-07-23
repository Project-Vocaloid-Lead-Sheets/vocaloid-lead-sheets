from gdrive_session import GDriveSession

import os
import enum
import pathlib

class SongRecord:
    def __init__(self, name: str):
        self.name = name
        self.pdfs_full = {}
        self.pdfs_tv = {}

    def has_any_full(self):
        return any(v for v in self.pdfs_full.values())

    def has_any_tv(self):
        return any(v for v in self.pdfs_tv.values())

    def compute_hyperlinks_full(self):
        return {k: f"https://drive.google.com/uc?export=download&id={v['id']}" for k, v in self.pdfs_full.items()}

    def compute_hyperlinks_tv(self):
        return {k: f"https://drive.google.com/uc?export=download&id={v['id']}" for k, v in self.pdfs_tv.items()}

class SongDataAccess:
    CHART_BASE_DIR = "Lead Sheets"
    TRANSCRIPTIONS = ['Vocals', 'Bb', 'C', 'Eb', 'F', 'G', 'Alto', 'Bass']

    def __init__(self, session: GDriveSession):
        self._session = session

    # TODO: create a song record retrieval but by song ID
    def get_record_by_attrs(self, song_name: str, song_producer: str) -> SongRecord:
        song_file_basename = f"{song_producer} - {song_name}"
        full_chart_dir = os.path.join(self.CHART_BASE_DIR, song_file_basename)

        file_drive_ids = self._session.find_files_in_dir(pathlib.Path(full_chart_dir))
        filename_to_meta = {song["name"] : song for song in file_drive_ids}
        record = SongRecord(song_name)
        for transcription in self.TRANSCRIPTIONS:
            song_filename = f"{song_file_basename}-{transcription}.pdf"
            if song_filename in filename_to_meta.keys():
                record.pdfs_full[transcription] = filename_to_meta[song_filename]

            song_filename = f"{song_file_basename} - TV-{transcription}.pdf"
            if song_filename in filename_to_meta.keys():
                record.pdfs_tv[transcription] = filename_to_meta[song_filename]

        record.pdfs_full = {k: v for k, v in record.pdfs_full.items() if v}
        record.pdfs_tv = {k: v for k, v in record.pdfs_tv.items() if v}

        return record

def main():
    import argparse
    parser = argparse.ArgumentParser("SongDataAccess direct query tool")
    parser.add_argument("-n", "--name", help="Song Name", required=True)
    parser.add_argument("-p", "--producer", help="Song Producer", required=True)

    args = vars(parser.parse_args())

    session = GDriveSession()
    data_access = SongDataAccess(session)
    record = data_access.get_record_by_attrs(args["name"], args["producer"])

    import pprint
    print(f"Song: {record.name}")
    print(f"Full Transcriptions:")
    pprint.pprint(record.pdfs_full)
    pprint.pprint(record.compute_hyperlinks_full())
    print(f"TV Transcriptions:")
    pprint.pprint(record.pdfs_tv)
    pprint.pprint(record.compute_hyperlinks_tv())

if __name__ == "__main__":
    main()
