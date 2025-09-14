#!/usr/bin/env python3
"""
Database Integration for PlantVision
Provides SQLite database operations for plant data management
"""

import sqlite3
import json
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

class PlantDatabase:
    """SQLite database manager for plant data"""
    
    def __init__(self, db_path: str = "data/plants.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Plants table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id TEXT UNIQUE NOT NULL,
                label TEXT DEFAULT 'unknown',
                area REAL DEFAULT 0,
                bbox_x INTEGER DEFAULT 0,
                bbox_y INTEGER DEFAULT 0,
                bbox_width INTEGER DEFAULT 0,
                bbox_height INTEGER DEFAULT 0,
                mean_bgr_r REAL DEFAULT 0,
                mean_bgr_g REAL DEFAULT 0,
                mean_bgr_b REAL DEFAULT 0,
                image_format TEXT DEFAULT 'jpg',
                image_width INTEGER DEFAULT 0,
                image_height INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Images table (stores base64 encoded images)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plant_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER,
                image_type TEXT NOT NULL, -- 'crop', 'highlight', 'raw'
                image_data TEXT NOT NULL, -- base64 encoded
                image_format TEXT DEFAULT 'jpg',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plant_id) REFERENCES plants (id) ON DELETE CASCADE
            )
        """)
        
        # Telemetry table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER,
                timestamp INTEGER NOT NULL,
                data TEXT NOT NULL, -- JSON string
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plant_id) REFERENCES plants (id) ON DELETE CASCADE
            )
        """)
        
        # Indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_plants_plant_id ON plants(plant_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_plant_id ON telemetry(plant_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp)")
        
        conn.commit()
        conn.close()
    
    def save_plant_data(self, plant_data: Dict[str, Any]) -> int:
        """Save plant data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert or update plant
            cursor.execute("""
                INSERT OR REPLACE INTO plants 
                (plant_id, label, area, bbox_x, bbox_y, bbox_width, bbox_height,
                 mean_bgr_r, mean_bgr_g, mean_bgr_b, image_format, image_width, image_height)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(plant_data.get('plant_id', 0)),
                plant_data.get('label', 'unknown'),
                plant_data.get('area', 0),
                plant_data.get('bbox', [0,0,0,0])[0],
                plant_data.get('bbox', [0,0,0,0])[1],
                plant_data.get('bbox', [0,0,0,0])[2],
                plant_data.get('bbox', [0,0,0,0])[3],
                plant_data.get('mean_bgr', [0,0,0])[0],
                plant_data.get('mean_bgr', [0,0,0])[1],
                plant_data.get('mean_bgr', [0,0,0])[2],
                plant_data.get('image_format', 'jpg'),
                plant_data.get('image_size', [0,0])[0],
                plant_data.get('image_size', [0,0])[1]
            ))
            
            plant_db_id = cursor.lastrowid
            
            # Save images if present
            if 'raw_image_base64' in plant_data:
                cursor.execute("""
                    INSERT INTO plant_images (plant_id, image_type, image_data, image_format)
                    VALUES (?, 'raw', ?, ?)
                """, (plant_db_id, plant_data['raw_image_base64'], plant_data.get('image_format', 'jpg')))
            
            # Save telemetry
            cursor.execute("""
                INSERT INTO telemetry (plant_id, timestamp, data)
                VALUES (?, ?, ?)
            """, (plant_db_id, plant_data.get('timestamp', 0), json.dumps(plant_data)))
            
            conn.commit()
            return plant_db_id
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_plant_data(self, plant_id: str) -> Optional[Dict[str, Any]]:
        """Get plant data by plant_id"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.*, pi.image_data as raw_image_base64
            FROM plants p
            LEFT JOIN plant_images pi ON p.id = pi.plant_id AND pi.image_type = 'raw'
            WHERE p.plant_id = ?
            ORDER BY p.updated_at DESC
            LIMIT 1
        """, (str(plant_id),))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Convert row to dictionary
        columns = [desc[0] for desc in cursor.description]
        plant_data = dict(zip(columns, row))
        
        # Reconstruct bbox and mean_bgr
        plant_data['bbox'] = [
            plant_data['bbox_x'], plant_data['bbox_y'],
            plant_data['bbox_width'], plant_data['bbox_height']
        ]
        plant_data['mean_bgr'] = [
            plant_data['mean_bgr_r'], plant_data['mean_bgr_g'], plant_data['mean_bgr_b']
        ]
        plant_data['image_size'] = [plant_data['image_width'], plant_data['image_height']]
        
        return plant_data
    
    def get_all_plants(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all plants with latest data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.*, pi.image_data as raw_image_base64
            FROM plants p
            LEFT JOIN plant_images pi ON p.id = pi.plant_id AND pi.image_type = 'raw'
            ORDER BY p.updated_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        plants = []
        for row in rows:
            columns = [desc[0] for desc in cursor.description]
            plant_data = dict(zip(columns, row))
            
            # Reconstruct bbox and mean_bgr
            plant_data['bbox'] = [
                plant_data['bbox_x'], plant_data['bbox_y'],
                plant_data['bbox_width'], plant_data['bbox_height']
            ]
            plant_data['mean_bgr'] = [
                plant_data['mean_bgr_r'], plant_data['mean_bgr_g'], plant_data['mean_bgr_b']
            ]
            plant_data['image_size'] = [plant_data['image_width'], plant_data['image_height']]
            
            plants.append(plant_data)
        
        return plants
    
    def update_plant_label(self, plant_id: str, label: str) -> bool:
        """Update plant label"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE plants 
                SET label = ?, updated_at = CURRENT_TIMESTAMP
                WHERE plant_id = ?
            """, (label, str(plant_id)))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_plant_history(self, plant_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get historical telemetry data for a plant"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.timestamp, t.data
            FROM telemetry t
            JOIN plants p ON t.plant_id = p.id
            WHERE p.plant_id = ?
            ORDER BY t.timestamp DESC
            LIMIT ?
        """, (str(plant_id), limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'timestamp': row[0],
                'data': json.loads(row[1])
            })
        
        return history
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old telemetry data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_timestamp = int((datetime.now().timestamp() - (days * 24 * 60 * 60)) * 1000)
        
        cursor.execute("""
            DELETE FROM telemetry 
            WHERE timestamp < ?
        """, (cutoff_timestamp,))
        
        conn.commit()
        conn.close()
        
        print(f"Cleaned up telemetry data older than {days} days")

def main():
    """Example usage"""
    db = PlantDatabase()
    
    # Example plant data
    plant_data = {
        'plant_id': '001',
        'label': 'basil',
        'area': 1234.5,
        'bbox': [100, 200, 150, 300],
        'mean_bgr': [45, 120, 67],
        'image_format': 'jpg',
        'image_size': [150, 300],
        'raw_image_base64': 'base64_encoded_image_data_here',
        'timestamp': int(datetime.now().timestamp() * 1000)
    }
    
    # Save plant data
    plant_id = db.save_plant_data(plant_data)
    print(f"Saved plant with ID: {plant_id}")
    
    # Retrieve plant data
    retrieved = db.get_plant_data('001')
    print(f"Retrieved plant: {retrieved}")
    
    # Get all plants
    all_plants = db.get_all_plants()
    print(f"Total plants: {len(all_plants)}")

if __name__ == "__main__":
    main()
