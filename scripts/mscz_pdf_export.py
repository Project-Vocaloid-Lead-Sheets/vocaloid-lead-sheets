#!/usr/bin/env python

import os
import json
import re
import shutil
import pathlib
import contextlib
import tempfile
import logging
import zipfile
import subprocess
import xml.etree.ElementTree

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
_logger = logging.getLogger(__name__)

def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


class MuseScoreExporter:
    def __init__(self, input_dir: str, output_dir: str):
        self._input_dir = pathlib.Path(input_dir)
        self._output_dir = pathlib.Path(output_dir)

        self._mscz_full_dir = self._output_dir / "full"
        self._mscz_tv_dir = self._output_dir / "tv"


    def do_extract(self):
        self._process_discover_mscz_copy_files()
        self._process_pdf_mass_export_dir(self._mscz_full_dir)
        self._process_pdf_mass_export_dir(self._mscz_tv_dir)


    def _process_discover_mscz_copy_files(self):
        mscz_paths: list[tuple(pathlib.Path, pathlib.Path)] = []
        os.makedirs(self._mscz_full_dir, exist_ok=True)
        os.makedirs(self._mscz_tv_dir, exist_ok=True)

        for path in self._input_dir.rglob("*"):
            if path.is_file() and  path.suffix.lower() == ".mscz":
                dst_name = f"{slugify(path.stem)}.mscz"
                subdir_name = "tv" if path.stem.lower().endswith("(tv size)") else "full"
                mscz_paths.append((path, self._output_dir / subdir_name / dst_name))

        for src_path, dst_path in mscz_paths:
            shutil.copy2(src_path, dst_path)

        _logger.info(f"Copied {len(mscz_paths)} mscz files ({self._input_dir} -> {self._output_dir})")


    def _process_pdf_mass_export_dir(self, directory: pathlib.Path):
        mass_export_job: list[dict] = []
        for path in directory.rglob("*.mscz"):
            version = MuseScoreExporter._get_musescore_version(path)
            if not MuseScoreExporter._is_musescore_4_or_newer(version):
                _logger.warning(f"{path} was built with Musescore v{version} - skipping")
                continue

            candidate_parts = self._find_export_candidates(path)
            job = MuseScoreExporter._create_musescore_job(path, path.parent)
            mass_export_job.append(job)

        _logger.info(f"Performing mass export of {len(mass_export_job)} mscz files...")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", dir=".", encoding="utf-8", delete=False) as job_file:
            json.dump(mass_export_job, job_file)
            job_file.flush()

            job_path = pathlib.Path(job_file.name).name
            subprocess.run(["docker", "compose", "run", "--rm", "musescore", "--job", job_path], check=True)


    def _find_export_candidates(self, mscz_path: pathlib.Path, min_size: int = 64 * 1024) -> list[str]:
        candidates = []

        with zipfile.ZipFile(mscz_path) as archive:
            for info in archive.infolist():
                path = pathlib.PurePosixPath(info.filename)

                # 1. Skip contents that aren't part excerpts or that are too small (heuristic of min_size)
                if path.suffix.lower() != ".mscx" or not path.parts or path.parts[0] != "Excerpts":
                    continue

                _, part_name = path.stem.split("_", 1)
                candidates.append(part_name)
        return sorted(candidates)


    def _get_musescore_version(mscz_path: pathlib.Path) -> str | None:
        with zipfile.ZipFile(mscz_path) as archive:
            for info in archive.infolist():
                path = pathlib.PurePosixPath(info.filename)

                # Main score is the root-level .mscx, not an excerpt.
                if len(path.parts) == 1 and path.suffix.lower() == ".mscx":
                    root = xml.etree.ElementTree.fromstring(archive.read(info))
                    version = root.findtext("programVersion")
                    return version

        return None


    def _is_musescore_4_or_newer(version: str | None) -> bool:
        return False if version is None else int(version.split(".", 1)[0]) >= 4


    def _create_musescore_job(mscz_path: pathlib.Path, output_dir: pathlib.Path) -> dict:
        job = { "in": str(mscz_path), "out": [[str(output_dir / f"{mscz_path.stem}-"), ".pdf"]]}
        return job


def main():
    import argparse
    import pprint
    import tabulate
    parser = argparse.ArgumentParser(description="Musescore PDF mass export utility")

    parser.add_argument("-i", "--input", required=True, help="Path to directory with .mscz files within")
    parser.add_argument("-o", "--output", required=True, help="Path to output directory to mass-export PDFs")

    args = vars(parser.parse_args())
    extractor = MuseScoreExporter(args["input"], args["output"])
    extractor.do_extract()



if __name__ == "__main__":
    main()
