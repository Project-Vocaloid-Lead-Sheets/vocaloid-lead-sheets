#!/usr/bin/env python3

import os
import sys
import gspread
import json
import logging
import argparse
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re
import hashlib
from typing import Dict, List, Any, Optional

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
    logger.info("ℹ️ python-dotenv not installed, using environment variables only")

class SongSyncManager:
    def __init__(self, force_sync: bool = False):
        self.sheet = None
        self.sync_state_file = '.sync_state.json'
        self.force_sync = force_sync
        
        # Set /data as JSON file output directory
        self.frontend_data_dir = os.environ.get('FRONTEND_DATA_DIR', 'frontend/src/data')
        # Path for the committed generated manifest that persists across CI runs
        self.generated_manifest_path = os.path.join(self.frontend_data_dir, 'generated-manifest.json')
        
        # PDF storage directory
        self.pdf_dir = os.path.join('frontend', 'public', 'pdfs')
        os.makedirs(self.pdf_dir, exist_ok=True)
        
    def slugify(self, text: str) -> str:
        """Convert text to a URL-friendly slug"""
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')

    def setup_google_sheets(self) -> None:
        """Set up Google Sheets API connection with better error handling and .env support"""
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
            
            client = gspread.authorize(creds)
            
            sheet_id = os.environ.get('GOOGLE_SHEET_ID')
            if not sheet_id:
                raise ValueError("GOOGLE_SHEET_ID environment variable not set")
            
            # Try to open the sheet and get specific worksheet
            workbook = client.open_by_key(sheet_id)
            
            # Get worksheet by name or index
            worksheet_name = os.environ.get('GOOGLE_SHEET_WORKSHEET_NAME')
            worksheet_index = os.environ.get('GOOGLE_SHEET_WORKSHEET_INDEX')
            
            if worksheet_name:
                logger.info(f"Using worksheet by name: '{worksheet_name}'")
                self.sheet = workbook.worksheet(worksheet_name)
            elif worksheet_index:
                # Convert to 0-based index (user provides 1-based)
                index = int(worksheet_index) - 1
                logger.info(f"Using worksheet by index: {index + 1} ('{workbook.worksheets()[index].title}')")
                self.sheet = workbook.worksheets()[index]
            else:
                logger.info("Using first worksheet (default)")
                self.sheet = workbook.sheet1  # Use first worksheet
            
            logger.info(f"Successfully connected to Google Sheet: {sheet_id}")
            logger.info(f"Active worksheet: '{self.sheet.title}'")

            # Save spreadsheet id for later use
            self.spreadsheet_id = sheet_id
            
        except Exception as e:
            logger.error(f"Failed to setup Google Sheets connection: {e}")
            raise

    def fetch_accepted_songs(self) -> List[Dict[str, Any]]:
        """Fetch accepted songs with enhanced validation and hyperlink extraction"""
        try:
            records = self.sheet.get_all_records()
            
            # Get hyperlinks for video columns
            hyperlinks_data = self._extract_hyperlinks_simple()
            
            # Filter for accepted songs and under review songs, validate required fields
            accepted_songs = []
            required_fields = ['Song Name', 'Status']
            
            for i, record in enumerate(records, start=2):  # Start at 2 for sheet row numbers
                status = str(record.get('Status', '')).lower().strip()
                original_status = str(record.get('Status', '')).strip()
                song_name = str(record.get('Song Name', '')).strip()
                
                # Log all statuses for debugging
                if song_name:
                    logger.info(f"Row {i}: '{song_name}' has status: '{original_status}' (normalized: '{status}')")
                
                # Accept both completed and under review (with flexible matching)
                valid_statuses = ['completed', 'under review']
                if status not in valid_statuses:
                    if status:  # Only log if there's actually a status value
                        logger.warning(f"Row {i}: Skipping song '{song_name}' with status '{original_status}' (not in valid statuses)")
                    continue
                
                # Validate required fields
                missing_fields = [field for field in required_fields if not record.get(field)]
                if missing_fields:
                    logger.warning(f"Row {i}: Missing required fields: {missing_fields}")
                    continue
                
                # Clean and validate song name
                if not song_name:
                    logger.warning(f"Row {i}: Empty song name")
                    continue
                
                # Check if at least one PDF is provided (check both hyperlinks and text)
                pdf_columns = ['Vocals', 'Bb', 'C', 'Eb', 'F']
                has_pdf = False
                
                # Check hyperlinks first
                if i in hyperlinks_data:
                    hyperlinks_for_row = hyperlinks_data[i]
                    has_pdf = any(col in hyperlinks_for_row for col in pdf_columns)
                
                # Fallback to text validation if no hyperlinks found
                if not has_pdf:
                    has_pdf = any(self._validate_drive_id(record.get(col, '')) for col in pdf_columns)
                
                if not has_pdf:
                    logger.warning(f"Row {i}: No valid PDF files found for '{song_name}'")
                    continue
                
                # Add hyperlink data if available
                if i in hyperlinks_data:
                    record['_hyperlinks'] = hyperlinks_data[i]
                
                accepted_songs.append(record)
            
            logger.info(f"Found {len(accepted_songs)} valid songs (completed + under review)")
            return accepted_songs
            
        except Exception as e:
            logger.error(f"Failed to fetch songs from sheet: {e}")
            raise

    def _extract_hyperlinks_simple(self) -> Dict[int, Dict[str, str]]:
        """Extract hyperlinks from chip format using Google Sheets API"""
        try:
            # Get the credentials and make direct API calls
            import requests
            
            # Get the access token from gspread client
            client = self.sheet.spreadsheet.client
            credentials = client.auth
            
            # Refresh token if needed
            if hasattr(credentials, 'token') and hasattr(credentials, 'refresh'):
                if credentials.expired:
                    credentials.refresh(requests.Request())
            
            access_token = credentials.token
            
            # Construct the API URL for getting grid data with chip information
            spreadsheet_id = self.sheet.spreadsheet.id
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
            
            params = {
                'includeGridData': 'true',
                'ranges': f"'{self.sheet.title}'!A:Z",
                'fields': 'sheets.data.rowData.values.chipRuns,sheets.data.rowData.values.formattedValue'
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            hyperlinks_by_row = {}
            
            if 'sheets' in data and len(data['sheets']) > 0:
                sheet_data = data['sheets'][0]
                if 'data' in sheet_data and len(sheet_data['data']) > 0:
                    grid_data = sheet_data['data'][0]
                    
                    if 'rowData' in grid_data:
                        # Get header row to map column indices to names
                        headers = []
                        if len(grid_data['rowData']) > 0 and 'values' in grid_data['rowData'][0]:
                            for cell in grid_data['rowData'][0]['values']:
                                headers.append(cell.get('formattedValue', ''))
                        
                        # Process data rows (skip header)
                        for row_idx, row_data in enumerate(grid_data['rowData'][1:], start=2):
                            if 'values' not in row_data:
                                continue
                            
                            row_hyperlinks = {}
                            
                            for col_idx, cell_data in enumerate(row_data['values']):
                                # Look for chipRuns with richLinkProperties
                                if 'chipRuns' in cell_data:
                                    for chip_run in cell_data['chipRuns']:
                                        if 'chip' in chip_run and 'richLinkProperties' in chip_run['chip']:
                                            uri = chip_run['chip']['richLinkProperties'].get('uri')
                                            if uri and col_idx < len(headers):
                                                col_name = headers[col_idx]
                                                # Include both link columns and PDF columns
                                                if col_name and ('link' in col_name.lower() or col_name in ['Vocals', 'Bb', 'C', 'Eb', 'F', 'G', 'Alto', 'Bass', 'Percussion', 'Youtube', 'Transcriber']):
                                                    row_hyperlinks[col_name] = uri
                                                    logger.debug(f"Found link in row {row_idx}, col {col_name}: {uri}")
                            
                            if row_hyperlinks:
                                hyperlinks_by_row[row_idx] = row_hyperlinks
            
            logger.info(f"Extracted hyperlinks for {len(hyperlinks_by_row)} rows")
            return hyperlinks_by_row
            
        except Exception as e:
            logger.warning(f"Failed to extract hyperlinks: {e}")
            return {}

    def normalize_song_data(self, song: Dict[str, Any], existing_song_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Normalize song data based on the sheet structure"""
        # Parse PDFs with change detection
        pdfs, links = self._parse_pdfs_new(song, existing_song_data)
        
        # Map sheet columns to JSON format
        normalized = {
            'title': str(song.get('Song Name', '')).strip(),
            'alternativeNames': self._parse_alternative_names(song.get('Alternative Names', '')),
            'producer': str(song.get('Producer', '')).strip(),
            'additionalProducers': self._parse_comma_separated(song.get('Additional Producers (comma sep)', '')),
            'singer': str(song.get('Original Voice', '')).strip(),
            'additionalVoices': self._parse_comma_separated(song.get('Additional Voices (comma sep)', '')),
            'releaseDate': self._format_date(song.get('Release Date (ISO)', '')),
            'bpm': self._parse_bpm(song.get('BPM', '')),
            'labels': self._parse_comma_separated(song.get('Labels (comma sep)', '')),
            'transcriber': str(song.get('Transcriber', '')).strip(),
            'videoLinks': self._parse_video_links_new(song),
            'pdfs': pdfs,
            'links': links,
            'metadata': {
                'status': self._normalize_status(song.get('Status', ''))
            }
        }
        
        return normalized

    def _normalize_status(self, status: Any) -> str:
        """Normalize status to standard values"""
        if not status:
            return 'completed'  # Default status
        
        status_lower = str(status).lower().strip()
        
        # Map various status values to standardized ones
        if status_lower in ['completed', 'complete', 'done', 'finished']:
            return 'completed'
        elif status_lower in ['under review', 'underreview', 'in progress', 'in-progress', 'inprogress', 'review', 'pending']:
            return 'under review'
        else:
            # Log unknown status and default to completed
            logger.warning(f"Unknown status '{status}', defaulting to 'completed'")
            return 'completed'

    def _parse_alternative_names(self, alt_names: Any) -> List[str]:
        """Parse alternative names"""
        if not alt_names:
            return []
        return self._parse_comma_separated(alt_names)

    def _parse_comma_separated(self, value: Any) -> List[str]:
        """Parse comma-separated values"""
        if not value:
            return []
        
        value_str = str(value).strip()
        if not value_str:
            return []
        
        # Split by comma and clean up each item
        items = [item.strip() for item in value_str.split(',')]
        return [item for item in items if item]  # Remove empty items

    def _parse_video_links_new(self, song: Dict[str, Any]) -> Dict[str, str]:
        """Parse video links with chip link support"""
        links = {}
        
        # Get hyperlinks if available
        hyperlinks = song.get('_hyperlinks', {})
        
        # YouTube Link
        youtube_text = str(song.get('Youtube', '')).strip()
        youtube_url = hyperlinks.get('Youtube') or youtube_text
        
        if youtube_url:
            links['YouTube'] = youtube_url
        
        return links

    def _parse_pdfs_new(self, song: Dict[str, Any], existing_song_data: Optional[Dict[str, Any]] = None) -> tuple[Dict[str, str], Dict[str, str]]:
        """Parse PDF information with chip link support and download PDFs locally
        
        Returns a tuple of (pdfs, links) where:
        - pdfs: dict mapping key names to local PDF paths
        - links: dict mapping key names to Google Drive URLs
        """
        pdf_drive_links = {}
        pdfs = {}
        
        # Get hyperlinks if available
        hyperlinks = song.get('_hyperlinks', {})
        
        # Get song title for filename generation
        song_title = song.get('Song Name', '').strip()
        song_slug = self.slugify(song_title)
        
        # Get existing PDF links from previous sync (if any)
        existing_links = {}
        if existing_song_data:
            existing_links = existing_song_data.get('links', {})
        
        # Map the key columns to PDF entries
        key_mappings = {
            'Vocals': 'Vocals',
            'Bb': 'Bb',
            'C': 'C', 
            'Eb': 'Eb',
            'F': 'F',
            'G': 'G',
            'Alto': 'Alto',
            'Bass': 'Bass',
        }
        
        for column_name, pdf_key in key_mappings.items():
            drive_id = None
            
            # First try to get URL from extracted hyperlinks (chip format)
            if column_name in hyperlinks:
                drive_url = hyperlinks[column_name]
                drive_id = self._validate_drive_id(drive_url)
            else:
                # Fallback to text content validation
                drive_id = self._validate_drive_id(song.get(column_name, ''))
            
            if drive_id:
                # Store Google Drive link for reference
                current_drive_link = f"https://drive.google.com/file/d/{drive_id}/view"
                pdf_drive_links[pdf_key] = current_drive_link
            
                # Generate local filename with song name and key
                pdf_filename = f"{song_slug}/{song_slug}-{pdf_key.lower()}.pdf"
                pdf_path = os.path.join(self.pdf_dir, pdf_filename)
                
                # Check if we need to download:
                # 1. File doesn't exist locally, OR
                # 2. Drive link has changed (different file)
                should_download = False
                if not os.path.exists(pdf_path):
                    logger.info(f"PDF not found locally: {pdf_filename}")
                    should_download = True
                elif pdf_key in existing_links and existing_links[pdf_key] != current_drive_link:
                    logger.info(f"Drive link changed for {pdf_key} in {song_title}, will re-download")
                    should_download = True
                elif pdf_key not in existing_links:
                    # No previous link data, assume we should download to be safe
                    should_download = True
                else:
                    logger.info(f"PDF already exists and unchanged: {pdf_filename}")
                
                if should_download:
                    # Download PDF from Google Drive
                    if self.download_pdf_from_drive(drive_id, pdf_filename):
                        # Store local path instead of Google Drive URL
                        pdfs[pdf_key] = f"/pdfs/{pdf_filename}"
                    else:
                        # Fallback to Google Drive URL if download fails
                        logger.warning(f"Download failed for {pdf_key}, using Google Drive URL as fallback")
                        pdfs[pdf_key] = f"https://drive.google.com/file/d/{drive_id}/view"
                else:
                    # Use existing local path
                    pdfs[pdf_key] = f"/pdfs/{pdf_filename}"
        
        return pdfs, pdf_drive_links

    def _format_date(self, date_value: Any) -> str:
        """Format date as ISO (YYYY-MM-DD) if possible"""
        if not date_value:
            return ''

        date_str = str(date_value).strip()
        import re

        # Handle MM/DD/YYYY or MM-DD-YYYY
        m = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', date_str)
        if m:
            month, day, year = m.groups()
            # return as YYYYMMDD (no separators) to match frontend expectations
            return f"{year}{month.zfill(2)}{day.zfill(2)}"

        # Handle YYYY-MM-DD
        m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', date_str)
        if m:
            year, month, day = m.groups()
            return f"{year}{month.zfill(2)}{day.zfill(2)}"

        # Handle YYYYMMDD
        m = re.match(r'^(\d{4})(\d{2})(\d{2})$', date_str)
        if m:
            year, month, day = m.groups()
            return f"{year}{month}{day}"

        logger.warning(f"Could not parse date: {date_str}")
        # Fallback: remove non-digits to try to produce YYYYMMDD-like string
        digits = re.sub(r'\D', '', date_str)
        if len(digits) == 8:
            return digits
        return ''

    def _parse_bpm(self, bpm_value: Any) -> Optional[int]:
        """Parse BPM value from the sheet into an integer if possible"""
        if bpm_value is None:
            return None
        bpm_str = str(bpm_value).strip()
        if not bpm_str:
            return None

        # Try to extract a number (allow floats but store as int)
        try:
            # Remove common annotations like 'bpm' or 'BPM'
            bpm_clean = re.sub(r'[^0-9.]', '', bpm_str)
            if not bpm_clean:
                return None
            bpm_float = float(bpm_clean)
            return int(round(bpm_float))
        except Exception:
            logger.warning(f"Unable to parse BPM value: {bpm_value}")
            return None

    def _parse_labels(self, labels_value: Any) -> List[str]:
        """Parse labels from various formats - kept for compatibility"""
        return self._parse_comma_separated(labels_value)

    def _validate_drive_id(self, drive_id: Any) -> Optional[str]:
        """Validate and extract Google Drive file ID"""
        if not drive_id:
            return None
        
        drive_id = str(drive_id).strip()
        
        # Extract ID from various Google Drive URL formats
        if 'drive.google.com' in drive_id:
            if '/d/' in drive_id:
                drive_id = drive_id.split('/d/')[1].split('/')[0]
            elif 'id=' in drive_id:
                drive_id = drive_id.split('id=')[1].split('&')[0]
        
        # Validate ID format
        if len(drive_id) >= 20 and drive_id.replace('-', '').replace('_', '').isalnum():
            return drive_id
        
        return None

    def download_pdf_from_drive(self, file_id: str, output_filename: str) -> bool:
        """Download a PDF from Google Drive and save it locally"""
        try:
            import requests
            
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
            output_path = os.path.join(self.pdf_dir, output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(output_path)
            logger.info(f"Successfully downloaded PDF: {output_filename} ({file_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download PDF {file_id}: {e}")
            return False

    def cleanup_orphaned_pdfs(self, referenced_pdfs: set) -> None:
        """Remove PDF files that are no longer referenced in any song"""
        try:
            if not os.path.exists(self.pdf_dir):
                return
            
            deleted_count = 0
            
            # Walk through all PDF files
            for root, dirs, files in os.walk(self.pdf_dir):
                for file in files:
                    if not file.endswith('.pdf'):
                        continue
                    
                    # Get relative path from pdf_dir
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.pdf_dir)
                    
                    # Check if this PDF is referenced
                    if rel_path not in referenced_pdfs:
                        try:
                            os.remove(full_path)
                            deleted_count += 1
                            logger.info(f"Deleted orphaned PDF: {rel_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete orphaned PDF {rel_path}: {e}")
            
            # Clean up empty directories
            for root, dirs, files in os.walk(self.pdf_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):  # Empty directory
                            os.rmdir(dir_path)
                            logger.info(f"Removed empty directory: {os.path.relpath(dir_path, self.pdf_dir)}")
                    except Exception as e:
                        logger.warning(f"Failed to remove directory {dir_path}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} orphaned PDF(s)")
            else:
                logger.info("No orphaned PDFs found")
                
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned PDFs: {e}")

    def group_and_merge_songs(self, songs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Group songs by title - simplified for new structure"""
        grouped = {}
        
        for song in songs:
            title = str(song.get('Song Name', '')).strip()
            if not title:
                continue
            
            # Load existing song data if available
            existing_song_data = None
            filename = f"{self.slugify(title)}.json"
            filepath = os.path.join(self.frontend_data_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing_song_data = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load existing song data for {title}: {e}")
            
            # Normalize with existing data for comparison
            normalized = self.normalize_song_data(song, existing_song_data)
            
            # Create song entry
            grouped[title] = {
                'title': normalized['title'],
                'alternativeNames': normalized['alternativeNames'],
                'producer': normalized['producer'],
                'additionalProducers': normalized['additionalProducers'],
                'singer': normalized['singer'],
                'additionalVoices': normalized['additionalVoices'],
                'releaseDate': normalized['releaseDate'],
                'bpm': normalized.get('bpm'),
                'labels': normalized['labels'],
                'transcriber': normalized['transcriber'],
                'videoLinks': normalized['videoLinks'],
                'links': normalized['links'],
                'pdfs': normalized['pdfs'],
                'metadata': normalized['metadata'],
            }
        
        return grouped

    def update_frontend_files(self, grouped_songs: Dict[str, Dict[str, Any]]) -> None:
        """Update frontend data files"""
        # Ensure frontend data directory exists
        os.makedirs(self.frontend_data_dir, exist_ok=True)
        
        # Track all generated filenames for manifest
        generated_files = []
        
        # Track all referenced PDF paths for cleanup
        referenced_pdfs = set()

        # Single run timestamp used when a song is new or changed
        synced_at_now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        
        # Update individual JSON files
        for title, song_data in grouped_songs.items():
            filename = f"{self.slugify(title)}.json"
            filepath = os.path.join(self.frontend_data_dir, filename)
            generated_files.append(filename)
            
            # Track referenced PDFs for this song
            for pdf_path in song_data['pdfs'].values():
                if pdf_path.startswith('/pdfs/'):
                    # Convert /pdfs/song/file.pdf to song/file.pdf
                    rel_path = pdf_path[6:]  # Remove '/pdfs/' prefix
                    # Normalize path separators for the current OS
                    rel_path = rel_path.replace('/', os.sep)
                    referenced_pdfs.add(rel_path)
            
            # Create frontend-compatible format (simplified structure)
            frontend_data = {
                'title': song_data['title'],
                'alternativeNames': song_data.get('alternativeNames', []),
                'producer': song_data['producer'],
                'additionalProducers': song_data.get('additionalProducers', []),
                'singer': song_data['singer'],
                'additionalVoices': song_data.get('additionalVoices', []),
                'releaseDate': song_data['releaseDate'],
                'bpm': song_data.get('bpm'),
                'labels': song_data.get('labels', []),
                'transcriber': song_data.get('transcriber', ''),
                'videoLinks': song_data['videoLinks'],
                'links': song_data.get('links', {}),
                'pdfs': song_data['pdfs'],
                'status': song_data.get('metadata', {}).get('status', 'completed'),
            }

            # Preserve existing syncedAt if the file content (excluding syncedAt) has not changed
            existing_synced_at = None
            existing_core = None
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing_json = json.load(f)
                        existing_synced_at = existing_json.get('syncedAt')
                        # Drop syncedAt before comparison
                        existing_core = {k: v for k, v in existing_json.items() if k != 'syncedAt'}
                except Exception as e:
                    logger.warning(f"Failed to read existing song file for sync preservation: {filepath} ({e})")

            if existing_core is not None and existing_core == frontend_data and existing_synced_at:
                frontend_data['syncedAt'] = existing_synced_at
            else:
                frontend_data['syncedAt'] = synced_at_now
            
 
            with open(filepath, 'w', encoding='utf-8') as f:
                # Pretty-print with indentation and preserve insertion order so
                # fields appear in the readable order (title, alternativeNames, producer, ...).
                json.dump(frontend_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Updated frontend file: {filepath}")
        
        # Clean up orphaned PDFs
        self.cleanup_orphaned_pdfs(referenced_pdfs)
        
        # Update the song manifest for the frontend
        self.update_song_manifest(generated_files)

    def update_song_manifest(self, filenames: List[str]) -> None:
        """Update the TypeScript manifest file with available song files"""
        try:
            manifest_path = os.path.join('frontend', 'src', 'utils', 'songManifest.ts')
            
            # Sort filenames for consistency
            sorted_filenames = sorted(filenames)
            
            manifest_content = """// Auto-generated song manifest
// This file is automatically updated by the sync script

export const SONG_MANIFEST = [
%s
] as const

export type SongFilename = typeof SONG_MANIFEST[number]
""" % (chr(10).join(f'  {repr(filename)},' for filename in sorted_filenames))
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                f.write(manifest_content)
            
            logger.info(f"Updated song manifest with {len(filenames)} files: {manifest_path}")
            
        except Exception as e:
            logger.warning(f"Failed to update song manifest: {e}")

        # Also update a small generated-manifest.json that contains the current content hash
        # This file is committed and used by the workflow to detect meaningful changes.
        try:
            generated_manifest = {
                'songs': sorted(filenames),
            }
            # Write deterministic JSON
            os.makedirs(os.path.dirname(self.generated_manifest_path), exist_ok=True)
            with open(self.generated_manifest_path, 'w', encoding='utf-8') as f:
                json.dump(generated_manifest, f, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            logger.info(f"Wrote generated manifest: {self.generated_manifest_path}")
        except Exception as e:
            logger.warning(f"Failed to write generated manifest: {e}")


    def get_remote_sheet_modified_time(self) -> Optional[str]:
        """Fetch the remote spreadsheet's modifiedTime from the Drive API."""
        try:
            # Use the gspread client's credentials to get an access token
            client = self.sheet.spreadsheet.client
            credentials = client.auth

            # Ensure token is fresh
            import requests as _req
            if hasattr(credentials, 'token') and hasattr(credentials, 'refresh'):
                if getattr(credentials, 'expired', False):
                    credentials.refresh(_req.Request())

            access_token = getattr(credentials, 'token', None)
            if not access_token:
                return None

            drive_url = f"https://www.googleapis.com/drive/v3/files/{self.spreadsheet_id}"
            params = {'fields': 'modifiedTime'}
            headers = {'Authorization': f'Bearer {access_token}'}

            r = _req.get(drive_url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            return data.get('modifiedTime')
        except Exception as e:
            logger.warning(f"Unable to fetch remote sheet modified time: {e}")
            return None

    def read_generated_manifest(self) -> Dict[str, Any]:
        """Read the persisted generated-manifest.json (if present) to obtain previous songs listing/hash."""
        try:
            if os.path.exists(self.generated_manifest_path):
                with open(self.generated_manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read generated manifest: {e}")
        return {}

    def save_sync_state(self, content_hash: str = '', sheet_modified_time: str = '', total_songs: int = 0, forced: bool = False, changes_written: bool = False) -> None:
        """Save current sync state to .sync_state.json (not committed)"""
        # Read existing state to preserve lastSync if no changes
        existing_state = self.get_sync_state()
        
        state = {
            'lastCheck': datetime.now().isoformat(),
            'lastSync': datetime.now().isoformat() if changes_written else existing_state.get('lastSync', datetime.now().isoformat()),
            'contentHash': content_hash,
            'sheetModifiedTime': sheet_modified_time,
            'totalSongs': total_songs,
            'forcedSync': forced
        }
        
        with open(self.sync_state_file, 'w') as f:
            json.dump(state, f, indent=2)
        logger.info(f"Updated sync state: content_hash={content_hash[:8]}..., sheet_time={sheet_modified_time}")

    def get_sync_state(self) -> Dict[str, Any]:
        """Get last sync state"""
        if os.path.exists(self.sync_state_file):
            with open(self.sync_state_file, 'r') as f:
                return json.load(f)
        return {}

    def calculate_songs_hash(self, songs: List[Dict[str, Any]]) -> str:
        """Calculate hash of all songs for change detection"""
        songs_str = json.dumps(songs, sort_keys=True)
        return hashlib.md5(songs_str.encode()).hexdigest()

    def calculate_content_hash(self, grouped_songs: Dict[str, Dict[str, Any]]) -> str:
        """Calculate deterministic hash of the content that would be written to disk"""
        # Create a deterministic representation of all files that would be written
        content_dict = {}
        for title, song_data in sorted(grouped_songs.items()):
            filename = f"{self.slugify(title)}.json"
            frontend_data = {
                'title': song_data['title'],
                'alternativeNames': song_data.get('alternativeNames', []),
                'producer': song_data['producer'],
                'additionalProducers': song_data.get('additionalProducers', []),
                'singer': song_data['singer'],
                'additionalVoices': song_data.get('additionalVoices', []),
                'releaseDate': song_data['releaseDate'],
                'bpm': song_data.get('bpm'),
                'labels': song_data.get('labels', []),
                'transcriber': song_data.get('transcriber', ''),
                'videoLinks': song_data['videoLinks'],
                'links': song_data.get('links', {}),
                'pdfs': song_data['pdfs'],
                'status': song_data.get('metadata', {}).get('status', 'completed')
            }
            content_dict[filename] = frontend_data
        
        # Generate deterministic JSON and hash it
        content_json = json.dumps(content_dict, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        return hashlib.sha256(content_json.encode()).hexdigest()

    def calculate_hash_from_existing_files(self) -> Optional[str]:
        """Calculate hash from files already committed to the repo (for bootstrap)"""
        try:
            if not os.path.exists(self.frontend_data_dir):
                return None
            
            # Read all existing JSON files
            content_dict = {}
            json_files = [f for f in os.listdir(self.frontend_data_dir) if f.endswith('.json') and f != 'generated-manifest.json']
            
            if not json_files:
                return None
            
            for filename in sorted(json_files):
                filepath = os.path.join(self.frontend_data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content_dict[filename] = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to read {filename} for hash: {e}")
                    return None
            
            # Generate same deterministic hash as calculate_content_hash
            content_json = json.dumps(content_dict, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
            return hashlib.sha256(content_json.encode()).hexdigest()
            
        except Exception as e:
            logger.warning(f"Failed to calculate hash from existing files: {e}")
            return None

    def sync(self) -> bool:
        """Main sync function. Returns True if content changed (commit needed), False if no changes."""
        try:
            logger.info("Starting Google Sheet sync...")
            
            # Set up connection
            self.setup_google_sheets()
            
            # Step 1: Quick check - compare cached sheet time with current
            current_sheet_time = self.get_remote_sheet_modified_time() or ''
            last_state = self.get_sync_state()
            last_sheet_time = last_state.get('sheetModifiedTime', '')
            # Bootstrap mode: No cache but files exist (first CI run after local commit)
            if not last_state and os.path.exists(self.frontend_data_dir):
                logger.info("🔄 Bootstrap mode: No cache found but files exist. Calculating hash from committed files...")
                existing_hash = self.calculate_hash_from_existing_files()
    
                if existing_hash:
                    # Count existing JSON files
                    json_files = [f for f in os.listdir(self.frontend_data_dir) 
                                    if f.endswith('.json') and f != 'generated-manifest.json']
        
                    logger.info(f"✅ Bootstrap complete: Found {len(json_files)} existing songs, hash={existing_hash[:8]}...")
        
                    # Save bootstrap state
                    self.save_sync_state(
                        content_hash=existing_hash,
                        sheet_modified_time=current_sheet_time,
                        total_songs=len(json_files),
                        forced=False,
                        changes_written=False
                    )
        
                    # Now continue with normal flow to check if sheet has changes
                    last_state = self.get_sync_state()
                else:
                    logger.warning("⚠️ Bootstrap failed: Could not read existing files. Proceeding with full sync.")
            
            
            if not self.force_sync and current_sheet_time and current_sheet_time == last_sheet_time:
                logger.info(f"Sheet hasn't been modified since last sync ({current_sheet_time}). Skipping.")
                # Update lastCheck but not lastSync (no changes written)
                self.save_sync_state(
                    content_hash=old_content_hash,
                    sheet_modified_time=current_sheet_time,
                    total_songs=last_state.get('totalSongs', 0),
                    forced=False,
                    changes_written=False
                )
                return False  # No changes detected
            
            logger.info(f"Sheet modified time changed: {last_sheet_time} -> {current_sheet_time}")
            
            # Step 2: Fetch and process data
            songs = self.fetch_accepted_songs()
            grouped_songs = self.group_and_merge_songs(songs)
            
            # Step 3: Compute content hash
            new_content_hash = self.calculate_content_hash(grouped_songs)
            old_content_hash = last_state.get('contentHash', '')
            
            # Step 4: Check if content actually changed
            if not self.force_sync and new_content_hash == old_content_hash:
                logger.info("Sheet time changed but content is identical. Updating cache time only.")
                # Update cache with new time but don't write files or commit (no changes)
                self.save_sync_state(
                    content_hash=new_content_hash,
                    sheet_modified_time=current_sheet_time,
                    total_songs=len(songs),
                    forced=False,
                    changes_written=False
                )
                return False  # No changes in actual content
            
            # Step 5: Content changed - write files and prepare for commit
            if self.force_sync:
                logger.info(f"Force sync enabled. Writing {len(grouped_songs)} songs...")
            else:
                logger.info(f"Content changed (hash: {old_content_hash[:8]}... -> {new_content_hash[:8]}...). Writing files.")
            
            self.update_frontend_files(grouped_songs)
            
            # Update cache with new time and hash - changes were written
            self.save_sync_state(
                content_hash=new_content_hash,
                sheet_modified_time=current_sheet_time,
                total_songs=len(songs),
                forced=self.force_sync,
                changes_written=True
            )
            
            logger.info(f"✅ Sync completed! {len(grouped_songs)} songs written. Commit required.")
            return True  # Changes detected - commit needed
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Sync Google Sheet data to JSON files for the Vocaloid Lead Sheets project'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force sync even if no changes are detected'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check whether the remote sheet has changed compared to the committed generated-manifest.json and exit (no heavy fetch/write)'
    )
    
    args = parser.parse_args()
    
    sync_manager = SongSyncManager(force_sync=args.force)
    # If check-only requested, run lightweight check and exit accordingly
    if args.check_only:
        try:
            # Authenticate and get remote modified time
            sync_manager.setup_google_sheets()
            remote_time = sync_manager.get_remote_sheet_modified_time()

            # Read the committed generated manifest (if present)
            prev_manifest = sync_manager.read_generated_manifest()
            prev_time = prev_manifest.get('sheetModifiedTime')

            result = {
                'previous': prev_time,
                'remote': remote_time,
            }

            if not remote_time:
                # Could not determine remote time; treat as changed (non-zero exit)
                result['status'] = 'unknown'
                print(json.dumps(result, ensure_ascii=False))
                sys.exit(2)

            if prev_time == remote_time:
                result['status'] = 'unchanged'
                print(json.dumps(result, ensure_ascii=False))
                sys.exit(0)
            else:
                result['status'] = 'changed'
                print(json.dumps(result, ensure_ascii=False))
                sys.exit(2)
        except Exception as e:
            # If anything goes wrong, surface a non-zero exit so CI does not short-circuit
            print(json.dumps({'status': 'error', 'error': str(e)}))
            sys.exit(2)

    # Default behavior: run full sync
    has_changes = sync_manager.sync()
    
    # Output result for GitHub Actions to capture
    print(f"SYNC_CHANGES_DETECTED={str(has_changes).lower()}")
    
    # Return 0 for success (standard Unix convention)
    sys.exit(0)

if __name__ == "__main__":
    main()
