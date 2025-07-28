#!/usr/bin/env python3

import os
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
            
        except Exception as e:
            logger.error(f"Failed to setup Google Sheets connection: {e}")
            raise

    def fetch_accepted_songs(self) -> List[Dict[str, Any]]:
        """Fetch accepted songs with enhanced validation and hyperlink extraction"""
        try:
            records = self.sheet.get_all_records()
            
            # Get hyperlinks for video columns
            hyperlinks_data = self._extract_hyperlinks_simple()
            
            # Filter for accepted songs and validate required fields
            accepted_songs = []
            required_fields = ['Song Name', 'Status']
            
            for i, record in enumerate(records, start=2):  # Start at 2 for sheet row numbers
                status = str(record.get('Status', '')).lower().strip()
                
                if status != 'completed':
                    continue
                
                # Validate required fields
                missing_fields = [field for field in required_fields if not record.get(field)]
                if missing_fields:
                    logger.warning(f"Row {i}: Missing required fields: {missing_fields}")
                    continue
                
                # Clean and validate song name
                song_name = str(record.get('Song Name', '')).strip()
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
            
            logger.info(f"Found {len(accepted_songs)} valid accepted songs")
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

    def normalize_song_data(self, song: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize song data based on the sheet structure"""
        # Map sheet columns to JSON format
        normalized = {
            'title': str(song.get('Song Name', '')).strip(),
            'alternativeNames': self._parse_alternative_names(song.get('Alternative Names', '')),
            'producer': str(song.get('Producer', '')).strip(),
            'additionalProducers': self._parse_comma_separated(song.get('Additional Producers (comma sep)', '')),
            'singer': str(song.get('Original Voice', '')).strip(),
            'additionalVoices': self._parse_comma_separated(song.get('Additional Voices (comma sep)', '')),
            'releaseDate': self._format_date(song.get('Release Date (ISO)', '')),
            'labels': self._parse_comma_separated(song.get('Labels (comma sep)', '')),
            'transcriber': str(song.get('Transcriber', '')).strip(),
            'videoLinks': self._parse_video_links_new(song),
            'pdfs': self._parse_pdfs_new(song),
            'metadata': {
                'status': str(song.get('Status', '')).strip(),
                'lastUpdated': datetime.now().isoformat()
            }
        }
        
        return normalized

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

    def _parse_pdfs_new(self, song: Dict[str, Any]) -> Dict[str, str]:
        """Parse PDF information with chip link support"""
        pdfs = {}
        
        # Get hyperlinks if available
        hyperlinks = song.get('_hyperlinks', {})
        
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
            # First try to get URL from extracted hyperlinks (chip format)
            if column_name in hyperlinks:
                drive_url = hyperlinks[column_name]
                drive_id = self._validate_drive_id(drive_url)
                if drive_id:
                    pdfs[pdf_key] = f"https://drive.google.com/file/d/{drive_id}/view"
            else:
                # Fallback to text content validation
                drive_id = self._validate_drive_id(song.get(column_name, ''))
                if drive_id:
                    pdfs[pdf_key] = f"https://drive.google.com/file/d/{drive_id}/view"
        
        return pdfs

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
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # Handle YYYY-MM-DD
        m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', date_str)
        if m:
            year, month, day = m.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # Handle YYYYMMDD
        m = re.match(r'^(\d{4})(\d{2})(\d{2})$', date_str)
        if m:
            year, month, day = m.groups()
            return f"{year}-{month}-{day}"

        logger.warning(f"Could not parse date: {date_str}")
        return date_str

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

    def group_and_merge_songs(self, songs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Group songs by title - simplified for new structure"""
        grouped = {}
        
        for song in songs:
            normalized = self.normalize_song_data(song)
            title = normalized['title']
            
            if not title:
                continue
            
            # Create song entry
            grouped[title] = {
                'title': normalized['title'],
                'alternativeNames': normalized['alternativeNames'],
                'producer': normalized['producer'],
                'additionalProducers': normalized['additionalProducers'],
                'singer': normalized['singer'],
                'additionalVoices': normalized['additionalVoices'],
                'releaseDate': normalized['releaseDate'],
                'labels': normalized['labels'],
                'transcriber': normalized['transcriber'],
                'videoLinks': normalized['videoLinks'],
                'pdfs': normalized['pdfs'],
                'lastUpdated': datetime.now().isoformat()
            }
        
        return grouped

    def update_frontend_files(self, grouped_songs: Dict[str, Dict[str, Any]]) -> None:
        """Update frontend data files"""
        # Ensure frontend data directory exists
        os.makedirs(self.frontend_data_dir, exist_ok=True)
        
        # Track all generated filenames for manifest
        generated_files = []
        
        # Update individual JSON files
        for title, song_data in grouped_songs.items():
            filename = f"{self.slugify(title)}.json"
            filepath = os.path.join(self.frontend_data_dir, filename)
            generated_files.append(filename)
            
            # Create frontend-compatible format (simplified structure)
            frontend_data = {
                'title': song_data['title'],
                'alternativeNames': song_data.get('alternativeNames', []),
                'producer': song_data['producer'],
                'additionalProducers': song_data.get('additionalProducers', []),
                'singer': song_data['singer'],
                'additionalVoices': song_data.get('additionalVoices', []),
                'releaseDate': song_data['releaseDate'],
                'labels': song_data.get('labels', []),
                'transcriber': song_data.get('transcriber', ''),
                'videoLinks': song_data['videoLinks'],
                'pdfs': song_data['pdfs']
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(frontend_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Updated frontend file: {filepath}")
        
        # Update the song manifest for the frontend
        self.update_song_manifest(generated_files)

    def update_song_manifest(self, filenames: List[str]) -> None:
        """Update the TypeScript manifest file with available song files"""
        try:
            manifest_path = os.path.join('frontend', 'src', 'utils', 'songManifest.ts')
            
            # Sort filenames for consistency
            sorted_filenames = sorted(filenames)
            
            manifest_content = f"""// Auto-generated song manifest
// This file is automatically updated by the sync script
// Last updated: {datetime.now().isoformat()}

export const SONG_MANIFEST = [
{chr(10).join(f'  {repr(filename)},' for filename in sorted_filenames)}
] as const

export type SongFilename = typeof SONG_MANIFEST[number]
"""
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                f.write(manifest_content)
            
            logger.info(f"Updated song manifest with {len(filenames)} files: {manifest_path}")
            
        except Exception as e:
            logger.warning(f"Failed to update song manifest: {e}")

    def save_sync_state(self, songs_hash: str, forced: bool = False) -> None:
        """Save current sync state"""
        state = {
            'lastSync': datetime.now().isoformat(),
            'songsHash': songs_hash,
            'totalSongs': len(songs_hash),
            'forcedSync': forced
        }
        
        with open(self.sync_state_file, 'w') as f:
            json.dump(state, f, indent=2)

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

    def sync(self) -> None:
        """Main sync function"""
        try:
            logger.info("Starting Google Sheet sync...")
            
            # Set up connection
            self.setup_google_sheets()
            
            # Fetch accepted songs
            songs = self.fetch_accepted_songs()
            
            # Check if anything changed
            current_hash = self.calculate_songs_hash(songs)
            last_state = self.get_sync_state()
            
            if not self.force_sync and current_hash == last_state.get('songsHash'):
                logger.info("No changes detected. Skipping sync. Use --force to sync anyway.")
                return
            
            if self.force_sync:
                logger.info(f"Force sync enabled. Processing {len(songs)} songs...")
            else:
                logger.info(f"Changes detected. Processing {len(songs)} songs...")
            
            # Group and process songs
            grouped_songs = self.group_and_merge_songs(songs)
            
            # Generate frontend JSON files only
            self.update_frontend_files(grouped_songs)
            
            # Save sync state
            self.save_sync_state(current_hash, self.force_sync)
            
            logger.info(f"Sync completed successfully! Processed {len(grouped_songs)} unique songs.")
            
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
    
    args = parser.parse_args()
    
    sync_manager = SongSyncManager(force_sync=args.force)
    sync_manager.sync()

if __name__ == "__main__":
    main()
