#!/usr/bin/env python3
"""
Data Migration Script for PlantVision
Migrates from flat file structure to organized folder structure
"""

import os
import json
import shutil
from pathlib import Path

def migrate_plant_data():
    """Migrate plant data from flat structure to organized folders"""
    
    data_dir = Path("data")
    plants_dir = data_dir / "plants"
    
    # Create plants directory
    plants_dir.mkdir(exist_ok=True)
    
    migrated_count = 0
    legacy_files = []
    
    # Find all plant files
    for file_path in data_dir.glob("plant_*.json"):
        try:
            # Extract plant ID
            plant_id = file_path.stem.split("_")[1]
            plant_id_int = int(plant_id)
            
            # Create zero-padded plant directory
            plant_dir = plants_dir / f"plant_{plant_id_int:03d}"
            plant_dir.mkdir(exist_ok=True)
            
            # Read existing JSON data
            with open(file_path, 'r') as f:
                plant_data = json.load(f)
            
            # Add metadata
            plant_data["plant_directory"] = str(plant_dir)
            plant_data["migrated"] = True
            
            # Save to new location
            new_json_path = plant_dir / "data.json"
            with open(new_json_path, 'w') as f:
                json.dump(plant_data, f, indent=2)
            
            # Move image files
            crop_file = data_dir / f"plant_{plant_id}_crop.jpg"
            highlight_file = data_dir / f"plant_{plant_id}_highlight.jpg"
            
            if crop_file.exists():
                shutil.move(str(crop_file), str(plant_dir / "crop.jpg"))
                legacy_files.append(str(crop_file))
            
            if highlight_file.exists():
                shutil.move(str(highlight_file), str(plant_dir / "highlight.jpg"))
                legacy_files.append(str(highlight_file))
            
            # Keep legacy JSON for compatibility
            legacy_files.append(str(file_path))
            
            migrated_count += 1
            print(f"Migrated plant {plant_id_int:03d}")
            
        except Exception as e:
            print(f"Error migrating {file_path}: {e}")
    
    print(f"\nMigration complete!")
    print(f"Migrated {migrated_count} plants")
    print(f"Legacy files kept for compatibility: {len(legacy_files)}")
    
    # Create summary
    summary = {
        "migrated_plants": migrated_count,
        "legacy_files": legacy_files,
        "new_structure": {
            "plants_dir": str(plants_dir),
            "format": "plant_XXX/{crop.jpg, highlight.jpg, data.json}"
        }
    }
    
    with open(data_dir / "migration_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Migration summary saved to {data_dir / 'migration_summary.json'}")

def create_database_schema():
    """Create SQLite database schema for future use"""
    
    import sqlite3
    
    db_path = Path("data") / "plants.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plants (
            id INTEGER PRIMARY KEY,
            plant_id TEXT UNIQUE,
            label TEXT,
            area REAL,
            bbox_x INTEGER,
            bbox_y INTEGER,
            bbox_width INTEGER,
            bbox_height INTEGER,
            mean_bgr_r REAL,
            mean_bgr_g REAL,
            mean_bgr_b REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plant_images (
            id INTEGER PRIMARY KEY,
            plant_id INTEGER,
            image_type TEXT, -- 'crop', 'highlight', 'raw'
            image_data BLOB,
            image_format TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plant_id) REFERENCES plants (id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY,
            plant_id INTEGER,
            timestamp INTEGER,
            data JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plant_id) REFERENCES plants (id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    print(f"Database schema created at {db_path}")

if __name__ == "__main__":
    print("PlantVision Data Migration")
    print("=" * 40)
    
    # Check if data directory exists
    if not Path("data").exists():
        print("Error: data directory not found")
        exit(1)
    
    # Run migration
    migrate_plant_data()
    
    # Create database schema for future use
    print("\nCreating database schema for future use...")
    create_database_schema()
    
    print("\nMigration complete! The new structure is:")
    print("data/")
    print("├── plants/")
    print("│   ├── plant_000/")
    print("│   │   ├── crop.jpg")
    print("│   │   ├── highlight.jpg")
    print("│   │   └── data.json")
    print("│   └── plant_001/")
    print("│       └── ...")
    print("├── plants.db (SQLite database)")
    print("└── migration_summary.json")
