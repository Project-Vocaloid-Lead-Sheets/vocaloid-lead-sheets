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

from gdrive_session import GDriveSession

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
        self.downloads_performed = False  # Tracks if any PDF was re-downloaded in a run
        
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

    def setup_google_drive(self) -> None:
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

    def fetch_tv_size_sheets(self) -> Dict[str, Dict[str, Any]]:
        """Fetch TV size sheet data from the 'TV Size Sheets' worksheet.
        
        Returns a dict mapping song names to TV size metadata:
        {
            'Song Name': {
                'pdfs': {
                    'Vocals': '/pdfs/song-name-tv/song-name-tv-vocals.pdf',
                    'Bb': '/pdfs/song-name-tv/song-name-tv-bb.pdf',
                    ...
                },
                'tvSizeLength': '1:30'
            }
        }
        """
        try:
            # Try to get the TV Size Sheets worksheet
            workbook = self.sheet.spreadsheet
            tv_sheet = None
            
            try:
                tv_sheet = workbook.worksheet('TV Size Sheets')
                logger.info(f"Found 'TV Size Sheets' worksheet")
            except gspread.exceptions.WorksheetNotFound:
                logger.info("'TV Size Sheets' worksheet not found, skipping TV size PDFs")
                return {}
            
            records = tv_sheet.get_all_records()
            
            # Get hyperlinks for this worksheet
            hyperlinks_data = self._extract_hyperlinks_from_worksheet(tv_sheet)
            
            tv_size_pdfs = {}
            pdf_columns = ['Vocals', 'Bb', 'C', 'Eb', 'F', 'G', 'Alto', 'Bass']
            
            for i, record in enumerate(records, start=2):  # Start at 2 for sheet row numbers
                song_name = str(record.get('Song Name', '')).strip()
                
                if not song_name:
                    continue
                
                song_slug = self.slugify(song_name)
                pdfs = {}
                tv_size_length = self._parse_length(record.get('TV Size Length', ''))
                
                # Extract hyperlinks for this row if available
                row_hyperlinks = hyperlinks_data.get(i, {})
                
                # Parse PDF links for each instrument column
                for column_name in pdf_columns:
                    drive_id = None
                    
                    # First try hyperlinks (chip format)
                    if column_name in row_hyperlinks:
                        drive_url = row_hyperlinks[column_name]
                        drive_id = self._validate_drive_id(drive_url)
                    else:
                        # Fallback to text content
                        drive_id = self._validate_drive_id(record.get(column_name, ''))
                    
                    if drive_id:
                        # Use TV size subdirectory naming: /pdfs/{song-slug}-tv/{song-slug}-tv-{instrument}.pdf
                        pdf_filename = f"{song_slug}-tv/{song_slug}-tv-{column_name.lower()}.pdf"
                        pdf_path = os.path.join(self.pdf_dir, pdf_filename)
                        
                        # Fetch Drive metadata for change detection
                        metadata = self._get_drive_file_metadata(drive_id)
                        remote_md5 = metadata.get('md5Checksum') if metadata else None
                        
                        # Compare and download if needed
                        local_md5 = self._file_md5(pdf_path) if os.path.exists(pdf_path) else None
                        should_download = False
                        
                        if not os.path.exists(pdf_path):
                            logger.info(f"TV PDF not found locally: {pdf_filename}")
                            should_download = True
                        elif remote_md5 and local_md5 and remote_md5 != local_md5:
                            logger.info(f"Remote TV PDF changed for {column_name} in {song_name}, will re-download")
                            should_download = True
                        elif remote_md5 and not local_md5:
                            should_download = True
                        elif not remote_md5 and not os.path.exists(pdf_path):
                            should_download = True
                        else:
                            logger.info(f"TV PDF up to date: {pdf_filename}")
                        
                        if should_download:
                            if GDriveSession.download_file(drive_id, os.path.join(self.pdf_dir, pdf_filename)):
                                pdfs[column_name] = f"/pdfs/{pdf_filename}"
                                self.downloads_performed = True
                            else:
                                logger.warning(f"Failed to download TV PDF for {column_name}, keeping existing if present")
                                if os.path.exists(pdf_path):
                                    pdfs[column_name] = f"/pdfs/{pdf_filename}"
                        else:
                            pdfs[column_name] = f"/pdfs/{pdf_filename}"
                
                if pdfs or tv_size_length:
                    tv_size_pdfs[song_name] = {
                        'pdfs': pdfs,
                        'tvSizeLength': tv_size_length,
                    }
            
            logger.info(f"Found {len(tv_size_pdfs)} songs with TV size sheets")
            return tv_size_pdfs
            
        except Exception as e:
            logger.error(f"Failed to fetch TV size sheets: {e}")
            return {}

    def _extract_hyperlinks_from_worksheet(self, worksheet) -> Dict[int, Dict[str, str]]:
        """Extract hyperlinks from a specific worksheet using Google Sheets API"""
        try:
            import requests
            
            client = worksheet.spreadsheet.client
            credentials = client.auth
            
            if hasattr(credentials, 'token') and hasattr(credentials, 'refresh'):
                if getattr(credentials, 'expired', False):
                    credentials.refresh(requests.Request())
            
            access_token = getattr(credentials, 'token', None)
            if not access_token:
                return {}
            
            spreadsheet_id = worksheet.spreadsheet.id
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
            
            params = {
                'includeGridData': 'true',
                'ranges': f"'{worksheet.title}'!A:Z",
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
                        # Get header row
                        headers = []
                        if len(grid_data['rowData']) > 0 and 'values' in grid_data['rowData'][0]:
                            for cell in grid_data['rowData'][0]['values']:
                                headers.append(cell.get('formattedValue', ''))
                        
                        # Process data rows
                        for row_idx, row_data in enumerate(grid_data['rowData'][1:], start=2):
                            if 'values' not in row_data:
                                continue
                            
                            row_hyperlinks = {}
                            
                            for col_idx, cell_data in enumerate(row_data['values']):
                                if 'chipRuns' in cell_data:
                                    for chip_run in cell_data['chipRuns']:
                                        if 'chip' in chip_run and 'richLinkProperties' in chip_run['chip']:
                                            uri = chip_run['chip']['richLinkProperties'].get('uri')
                                            if uri and col_idx < len(headers):
                                                col_name = headers[col_idx]
                                                if col_name:
                                                    row_hyperlinks[col_name] = uri
                            
                            if row_hyperlinks:
                                hyperlinks_by_row[row_idx] = row_hyperlinks
            
            logger.info(f"Extracted hyperlinks for {len(hyperlinks_by_row)} rows from {worksheet.title}")
            return hyperlinks_by_row
            
        except Exception as e:
            logger.warning(f"Failed to extract hyperlinks from {worksheet.title}: {e}")
            return {}

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

    def normalize_song_data(self, song: Dict[str, Any], existing_song_data: Optional[Dict[str, Any]] = None, tv_size_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Normalize song data based on the sheet structure
        
        Args:
            song: Dict with song data from main Songs worksheet
            existing_song_data: Existing frontend JSON data for comparison (if available)
            tv_size_data: Dict containing TV size metadata for this song (from TV Size Sheets worksheet)
        """
        tv_size_data = tv_size_data or {}

        # Parse PDFs with change detection (Drive md5 checksums included)
        pdfs, links, pdf_checksums, downloaded_any = self._parse_pdfs_new(song, existing_song_data)
        if downloaded_any:
            self.downloads_performed = True
        
        # Map sheet columns to JSON format
        normalized = {
            'title': str(song.get('Song Name', '')).strip(),
            'alternativeNames': self._parse_alternative_names(song.get('Alternative Names', '')),
            'producer': str(song.get('Producer', '')).strip(),
            'additionalProducers': self._parse_comma_separated(song.get('Additional Producers (comma sep)', '')),
            'singer': str(song.get('Original Voice', '')).strip(),
            'additionalVoices': self._parse_comma_separated(song.get('Additional Voices (comma sep)', '')),
            'releaseDate': self._format_date(song.get('Release Date (ISO)', '')),
            'length': self._parse_length(song.get('Length', '')),
            'tvSizeLength': self._parse_length(tv_size_data.get('tvSizeLength', '')),
            'bpm': self._parse_bpm(song.get('BPM', '')),
            'labels': self._parse_comma_separated(song.get('Labels (comma sep)', '')),
            'transcriber': str(song.get('Transcriber', '')).strip(),
            'videoLinks': self._parse_video_links_new(song),
            'pdfs': pdfs,
            'pdfsTvSize': tv_size_data.get('pdfs', {}),
            'links': links,
            'pdfChecksums': pdf_checksums,
            # Track whether this song downloaded any PDFs this run for per-song syncedAt decisions
            'downloaded': downloaded_any,
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

    def _parse_pdfs_new(
        self, song: Dict[str, Any], existing_song_data: Optional[Dict[str, Any]] = None
    ) -> tuple[Dict[str, str], Dict[str, str], Dict[str, Optional[str]], bool]:
        """Parse PDF information with chip link support and download PDFs locally.

        Returns a tuple of (pdfs, links, checksums) where:
        - pdfs: dict mapping key names to local PDF paths
        - links: dict mapping key names to Google Drive URLs
        - checksums: dict mapping key names to the Drive md5Checksum (if available)
        - downloaded: True if any PDF was downloaded in this call
        """
        pdf_drive_links: Dict[str, str] = {}
        pdfs: Dict[str, str] = {}
        pdf_checksums: Dict[str, Optional[str]] = {}
        downloaded_any = False
        
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

                # Fetch Drive metadata (md5Checksum) to detect content changes without relying on sheet edits
                metadata = self._get_drive_file_metadata(drive_id)
                remote_md5 = metadata.get('md5Checksum') if metadata else None
                pdf_checksums[pdf_key] = remote_md5

                # Generate local filename with song name and key
                pdf_filename = f"{song_slug}/{song_slug}-{pdf_key.lower()}.pdf"
                pdf_path = os.path.join(self.pdf_dir, pdf_filename)

                # Compare remote checksum to local file checksum (if it exists)
                local_md5 = self._file_md5(pdf_path) if os.path.exists(pdf_path) else None

                should_download = False
                if not os.path.exists(pdf_path):
                    logger.info(f"PDF not found locally: {pdf_filename}")
                    should_download = True
                elif remote_md5 and local_md5 and remote_md5 != local_md5:
                    logger.info(f"Remote PDF changed for {pdf_key} in {song_title} (md5 mismatch), will re-download")
                    should_download = True
                elif remote_md5 and not local_md5:
                    # Local file unreadable or md5 unavailable; be safe and re-download
                    should_download = True
                elif not remote_md5:
                    # No checksum available from Drive; fall back to link-change heuristic
                    if pdf_key in existing_links and existing_links[pdf_key] != current_drive_link:
                        logger.info(f"Drive link changed for {pdf_key} in {song_title}, will re-download")
                        should_download = True
                    elif pdf_key not in existing_links:
                        should_download = True

                if should_download:
                    if GDriveSession.download_file(drive_id, os.path.join(self.pdf_dir, pdf_filename)):
                        pdfs[pdf_key] = f"/pdfs/{pdf_filename}"
                        downloaded_any = True
                        # Update checksum after download if remote md5 unavailable
                        if not remote_md5:
                            pdf_checksums[pdf_key] = self._file_md5(pdf_path)
                    else:
                        logger.warning(f"Download failed for {pdf_key}, keeping existing local file if present")
                        if os.path.exists(pdf_path):
                            pdfs[pdf_key] = f"/pdfs/{pdf_filename}"
                            pdf_checksums[pdf_key] = self._file_md5(pdf_path)
                        else:
                            pdfs[pdf_key] = f"https://drive.google.com/file/d/{drive_id}/view"
                else:
                    logger.info(f"PDF up to date: {pdf_filename}")
                    pdfs[pdf_key] = f"/pdfs/{pdf_filename}"

        return pdfs, pdf_drive_links, pdf_checksums, downloaded_any

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

    def _parse_length(self, length_value: Any) -> str:
        """Parse length value and normalize to M:SS format."""
        if length_value is None:
            return ''

        length_str = str(length_value).strip()
        if not length_str:
            return ''

        # MM:SS or M:SS
        m = re.match(r'^(\d{1,3}):(\d{2})$', length_str)
        if m:
            minutes = int(m.group(1))
            seconds = int(m.group(2))
            if 0 <= seconds <= 59:
                return f"{minutes}:{seconds:02d}"

        # HH:MM:SS (convert to total minutes:seconds)
        m = re.match(r'^(\d{1,2}):(\d{2}):(\d{2})$', length_str)
        if m:
            hours = int(m.group(1))
            minutes = int(m.group(2))
            seconds = int(m.group(3))
            if 0 <= minutes <= 59 and 0 <= seconds <= 59:
                total_minutes = (hours * 60) + minutes
                return f"{total_minutes}:{seconds:02d}"

        logger.warning(f"Could not parse length value: {length_str}")
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

    def _get_drive_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Fetch Drive file metadata (md5Checksum, modifiedTime, size) for change detection."""
        try:
            client = self.sheet.spreadsheet.client
            credentials = client.auth

            # Local import to avoid hard dependency at module import time
            import requests

            if hasattr(credentials, 'token') and hasattr(credentials, 'refresh'):
                try:
                    credentials.refresh(None)
                except Exception:
                    pass

            access_token = getattr(credentials, 'token', None)
            if not access_token:
                return {}

            url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
            params = {'fields': 'md5Checksum,modifiedTime,size'}
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            r = requests.get(url, params=params, headers=headers, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning(f"Failed to fetch Drive metadata for {file_id}: {e}")
            return {}

    def _file_md5(self, path: str) -> Optional[str]:
        """Compute md5 checksum of a local file if readable."""
        try:
            if not os.path.exists(path):
                return None
            hash_md5 = hashlib.md5()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.warning(f"Unable to hash file {path}: {e}")
            return None

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

    def group_and_merge_songs(self, songs: List[Dict[str, Any]], tv_size_pdfs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        """Group songs by title - simplified for new structure
        
        Args:
            songs: List of song records from main Songs worksheet
            tv_size_pdfs: Dict mapping song names to their TV size PDFs from TV Size Sheets worksheet
        """
        if tv_size_pdfs is None:
            tv_size_pdfs = {}
        
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
            
            # Get TV size metadata for this song if available
            song_tv_size_data = tv_size_pdfs.get(title, {})
            
            # Normalize with existing data for comparison
            normalized = self.normalize_song_data(song, existing_song_data, song_tv_size_data)
            
            # Create song entry
            grouped[title] = {
                'title': normalized['title'],
                'alternativeNames': normalized['alternativeNames'],
                'producer': normalized['producer'],
                'additionalProducers': normalized['additionalProducers'],
                'singer': normalized['singer'],
                'additionalVoices': normalized['additionalVoices'],
                'releaseDate': normalized['releaseDate'],
                'length': normalized.get('length', ''),
                'tvSizeLength': normalized.get('tvSizeLength', ''),
                'bpm': normalized.get('bpm'),
                'labels': normalized['labels'],
                'transcriber': normalized['transcriber'],
                'videoLinks': normalized['videoLinks'],
                'links': normalized['links'],
                'pdfChecksums': normalized.get('pdfChecksums', {}),
                'pdfs': normalized['pdfs'],
                'pdfsTvSize': normalized.get('pdfsTvSize', {}),
                'downloaded': normalized.get('downloaded', False),
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
            
            # Track TV size PDFs too
            for tv_pdf_path in song_data.get('pdfsTvSize', {}).values():
                if tv_pdf_path.startswith('/pdfs/'):
                    rel_path = tv_pdf_path[6:]  # Remove '/pdfs/' prefix
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
                'length': song_data.get('length', ''),
                'tvSizeLength': song_data.get('tvSizeLength', ''),
                'bpm': song_data.get('bpm'),
                'labels': song_data.get('labels', []),
                'transcriber': song_data.get('transcriber', ''),
                'videoLinks': song_data['videoLinks'],
                'links': song_data.get('links', {}),
                'pdfChecksums': song_data.get('pdfChecksums', {}),
                'pdfs': song_data['pdfs'],
                'pdfsTvSize': song_data.get('pdfsTvSize', {}),
                'status': song_data.get('metadata', {}).get('status', 'completed'),
            }

            # Snapshots to tell apart content-bearing changes (status + PDFs) from metadata-only changes
            content_snapshot = {
                'status': frontend_data['status'],
                'pdfs': frontend_data['pdfs'],
                'pdfsTvSize': frontend_data.get('pdfsTvSize', {}),
                'pdfChecksums': frontend_data.get('pdfChecksums', {}),
                'links': frontend_data.get('links', {}),
            }

            existing_updated_at = None
            existing_synced_at = None
            existing_content_snapshot = None
            existing_json = None

            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing_json = json.load(f)
                        existing_updated_at = existing_json.get('updatedAt')
                        existing_synced_at = existing_json.get('syncedAt')
                        existing_content_snapshot = {
                            'status': existing_json.get('status', 'completed'),
                            'pdfs': existing_json.get('pdfs', {}),
                            'pdfsTvSize': existing_json.get('pdfsTvSize', {}),
                            'pdfChecksums': existing_json.get('pdfChecksums', {}),
                            'links': existing_json.get('links', {}),
                        }
                except Exception as e:
                    logger.warning(f"Failed to read existing song file for sync preservation: {filepath} ({e})")

            content_changed = True if existing_content_snapshot is None else existing_content_snapshot != content_snapshot
            
            # Check if any field in the song data changed for syncedAt - exclude timestamps from comparison
            data_changed = True if existing_json is None else (
                {k: v for k, v in frontend_data.items()} != 
                {k: v for k, v in existing_json.items() if k not in ['syncedAt', 'updatedAt']}
            )

            # syncedAt: only update if this song's data actually changed (any field, including metadata)
            if data_changed:
                frontend_data['syncedAt'] = synced_at_now
            elif existing_synced_at:
                frontend_data['syncedAt'] = existing_synced_at
            else:
                frontend_data['syncedAt'] = synced_at_now

            # updatedAt: only bump when real content changed (status or PDFs) for showing recent activity
            if content_changed:
                frontend_data['updatedAt'] = synced_at_now
            elif existing_updated_at:
                frontend_data['updatedAt'] = existing_updated_at
            else:
                frontend_data['updatedAt'] = synced_at_now
            
 
            with open(filepath, 'w', encoding='utf-8') as f:
                # Pretty-print with indentation and preserve insertion order so
                # fields appear in the readable order (title, alternativeNames, producer, ...).
                json.dump(frontend_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Updated frontend file: {filepath}")

        # Remove per-song JSON files that no longer correspond to sheet rows
        try:
            existing_jsons = [
                f for f in os.listdir(self.frontend_data_dir)
                if f.endswith('.json') and f != 'generated-manifest.json'
            ]
            for stale_file in existing_jsons:
                if stale_file not in generated_files:
                    stale_path = os.path.join(self.frontend_data_dir, stale_file)
                    try:
                        os.remove(stale_path)
                        logger.info(f"Deleted removed-song JSON: {stale_file}")
                    except Exception as e:
                        logger.warning(f"Failed to delete removed-song JSON {stale_file}: {e}")
        except Exception as e:
            logger.warning(f"Failed to enumerate existing JSON files for cleanup: {e}")
        
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

    def save_sync_state(self, content_hash: str = '', total_songs: int = 0, forced: bool = False, changes_written: bool = False) -> None:
        """Save current sync state to .sync_state.json (not committed)."""
        existing_state = self.get_sync_state()

        state = {
            'lastCheck': datetime.now().isoformat(),
            'lastSync': datetime.now().isoformat() if changes_written else existing_state.get('lastSync', datetime.now().isoformat()),
            'contentHash': content_hash,
            'totalSongs': total_songs,
            'forcedSync': forced
        }

        with open(self.sync_state_file, 'w') as f:
            json.dump(state, f, indent=2)
        logger.info(f"Updated sync state: content_hash={content_hash[:8]}...")

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
                'length': song_data.get('length', ''),
                'tvSizeLength': song_data.get('tvSizeLength', ''),
                'bpm': song_data.get('bpm'),
                'labels': song_data.get('labels', []),
                'transcriber': song_data.get('transcriber', ''),
                'videoLinks': song_data['videoLinks'],
                'links': song_data.get('links', {}),
                'pdfChecksums': song_data.get('pdfChecksums', {}),
                'pdfs': song_data['pdfs'],
                'pdfsTvSize': song_data.get('pdfsTvSize', {}),
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
            self.setup_google_drive()
            self.downloads_performed = False
            
            last_state = self.get_sync_state()
            old_content_hash = last_state.get('contentHash', '')

            # Fetch and process data (always compute full state, including Drive md5 checksums)
            songs = self.fetch_accepted_songs()
            tv_size_pdfs = self.fetch_tv_size_sheets()
            grouped_songs = self.group_and_merge_songs(songs, tv_size_pdfs)
            new_content_hash = self.calculate_content_hash(grouped_songs)

            if not self.force_sync and new_content_hash == old_content_hash and not self.downloads_performed:
                logger.info("Content (including PDF md5) unchanged. Skipping writes.")
                self.save_sync_state(
                    content_hash=new_content_hash,
                    total_songs=len(songs),
                    forced=False,
                    changes_written=False
                )
                return False

            if self.force_sync:
                logger.info(f"Force sync enabled. Writing {len(grouped_songs)} songs...")
            elif self.downloads_performed and new_content_hash == old_content_hash:
                logger.info(f"PDFs were re-downloaded (md5 mismatch) even though hash is unchanged. Writing files.")
            else:
                logger.info(f"Content changed (hash: {old_content_hash[:8]}... -> {new_content_hash[:8]}...). Writing files.")
            
            self.update_frontend_files(grouped_songs)
            
            self.save_sync_state(
                content_hash=new_content_hash,
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
        help='Compute current content hash (including PDF md5) and exit without writing files'
    )
    
    args = parser.parse_args()
    
    sync_manager = SongSyncManager(force_sync=args.force)
    # If check-only requested, compute current hash (full evaluation) and exit accordingly
    if args.check_only:
        try:
            sync_manager.setup_google_drive()
            songs = sync_manager.fetch_accepted_songs()
            tv_size_pdfs = sync_manager.fetch_tv_size_sheets()
            grouped_songs = sync_manager.group_and_merge_songs(songs, tv_size_pdfs)
            current_hash = sync_manager.calculate_content_hash(grouped_songs)
            last_state = sync_manager.get_sync_state()
            previous_hash = last_state.get('contentHash', '')

            status = 'unchanged' if current_hash == previous_hash else 'changed'
            result = {
                'previousHash': previous_hash,
                'currentHash': current_hash,
                'status': status,
            }
            print(json.dumps(result, ensure_ascii=False))
            sys.exit(0 if status == 'unchanged' else 2)
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
