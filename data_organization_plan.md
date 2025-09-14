# Data Organization Improvement Plan

## Current Issues
- 3 files per plant: `plant_X_crop.jpg`, `plant_X_highlight.jpg`, `plant_X.json`
- 40+ plants = 120+ files in root data directory
- No raw image data in JSON
- Difficult to manage and find specific plant data

## Proposed Solutions

### Option 1: Folder-Based Organization
```
data/
├── frames/
│   ├── frame_raw.jpg
│   └── frame_annotated.jpg
├── plants/
│   ├── plant_000/
│   │   ├── crop.jpg
│   │   ├── highlight.jpg
│   │   ├── raw.jpg (base64 encoded)
│   │   └── data.json
│   ├── plant_001/
│   │   └── ...
│   └── plant_002/
└── config.json
```

### Option 2: Database Integration (SQLite)
```
data/
├── frames/
│   ├── frame_raw.jpg
│   └── frame_annotated.jpg
├── plants.db (SQLite database)
│   ├── plants table
│   ├── images table (blob storage)
│   └── telemetry table
└── config.json
```

### Option 3: Hybrid Approach
- Use folders for organization
- Add base64 images to JSON
- Optional SQLite for historical data
- Keep current structure for compatibility

## Implementation Plan
1. Create new folder structure
2. Update C++ app to save to new structure
3. Add base64 image encoding to JSON
4. Update web UI to handle new paths
5. Add migration script for existing data
6. Consider SQLite for advanced queries
