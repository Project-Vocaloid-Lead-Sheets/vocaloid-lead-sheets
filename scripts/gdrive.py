
import logging
import os
import requests

from pathlib import Path


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_pdf(file_id: str, output_filepath: Path) -> bool:
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