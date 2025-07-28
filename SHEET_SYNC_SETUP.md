# Google Sheet Sync System

This system automatically syncs completed song submissions from a Google Sheet to JSON files for the frontend application.

## Setup

### 1. Google Sheet Setup

The "Vocaloid Lead Sheets Progress" Google Sheet is used to track all submissions. Follow all submission guidelines and fill in the cells according to precedent. Songs will be synced to the repository the next time the sync is run and a song has changed from a non-completed status to a completed status.

### Important Notes:

- **Status column must be "completed"** for songs to sync
- **At least one PDF column** must have a valid Google Drive ID or URL (make sure it is open to sharing)
- **Use comma-separated fields** so that they can be parsed into arrays
- **Use smart chips for links** for readability, as they are automatically extracted and used

### 2. Authentication Setup

A [Google Service Account](https://console.cloud.google.com/) has been set up with the Google Sheets API enabled.
If you are a developer, message KOB for access to the Cloud project.
Then, you will have access to the account to download the JSON key file, which is needed for your local environment.

### 3. Environment Variables

Set these environment variables in an .env file for local sync testing:

- `GOOGLE_SHEET_ID` - The ID from the Google Sheet URL
- `GOOGLE_SERVICE_ACCOUNT_JSON_FILE` - Path to service account JSON file
- `GOOGLE_SHEET_WORKSHEET_NAME` - Name of specific worksheet tab

### 4. Running the Sync

The sync can be run in several ways:

**Manual Local Execution:**

```bash
# Install dependencies
python -m pip install -r requirements.txt

# Basic sync
python scripts/sheet_sync.py

# Force sync (ignore change detection and always refresh)
python scripts/sheet_sync.py --force
python scripts/sheet_sync.py -f
```

**GitHub Actions (if configured):**

- Automatically via cron schedule
- Manually via "Run workflow" button
- On push/PR events (if workflow configured)

**Change Detection:**

- Uses MD5 hashing to detect changes
- Skips sync if no changes found (unless --force used)
- Tracks sync state in `.sync_state.json`

### 5. Output

The sync creates:

- `frontend/src/data/*.json` - Individual JSON files for each song
- `frontend/src/utils/songManifest.ts` - TypeScript manifest with all available song files
- `.sync_state.json` - Tracks last sync state and hash

## File Structure

### JSON Sample Format (`frontend/src/data/*.json`)

```json
{
  "title": "Song Title",
  "alternativeNames": ["Alternative Name 1", "Alternative Name 2"],
  "producer": "Producer Name",
  "additionalProducers": ["Co-Producer"],
  "singer": "Vocaloid Name",
  "additionalVoices": ["Additional Voice"],
  "releaseDate": "2025-01-01",
  "labels": ["Hall of Myths", "Hall of Legends"],
  "transcriber": "Transcriber",
  "videoLinks": {
    "YouTube": "https://youtube.com/..."
  },
  "pdfs": {
    "Vocals": "https://drive.google.com/file/d/.../view",
    "C": "https://drive.google.com/file/d/.../view"
  }
}
```

### Song Manifest (`frontend/src/utils/songManifest.ts`)

```typescript
// Auto-generated song manifest
// Last updated: 2025-07-27T22:30:00.000Z

export const SONG_MANIFEST = [
  "cendrillon.json",
  "donut-hole.json",
  "senbonzakura.json",
  // ... more files
] as const;

export type SongFilename = (typeof SONG_MANIFEST)[number];
```

## Frontend Integration

The frontend loads song data using the generated JSON files and manifest:

1. **Dynamic Loading**: Uses the TypeScript manifest to load individual JSON files
2. **Store Integration**: Pinia store manages reactive song data
3. **Automatic Discovery**: New songs are automatically available after sync
4. **Type Safety**: TypeScript manifest provides compile-time file checking

### Usage in Components

```typescript
import { useSongsStore } from "@/stores/songs";
import { jsonLoader } from "@/utils/jsonLoader";

const songsStore = useSongsStore();

// Load songs (done automatically on app startup)
await jsonLoader.loadAllSongs();

// Access songs reactively
const songs = computed(() => songsStore.songs);

// Get specific song by slug
const song = songsStore.getSongBySlug("song-title");

// Access metadata
const producers = computed(() => songsStore.allProducers);
const singers = computed(() => songsStore.allSingers);
const labels = computed(() => songsStore.allLabels);
```
