# PlantVision Data Organization Plan v2.0

## Hierarchical Data Structure

### Primary Data Directories

```
/app/data/
├── config.json                    # System configuration
├── frame_raw.jpg                  # Latest camera capture  
├── frame_annotated.jpg           # Latest analysis overlay
├── ai_metrics.json               # AI processing metrics
├── classes_overrides.json        # Manual plant classifications
├── sprouts/                      # Early growth stage instances
│   ├── summary.json              # Sprout summary statistics
│   ├── sprout_000/              # Individual sprout data
│   │   ├── crop.jpg             # Cropped sprout image
│   │   ├── highlight.jpg        # Analysis visualization
│   │   └── data.json            # Sprout telemetry & metadata
│   └── sprout_001/              # Additional sprouts...
└── plants/                      # Mature plant instances
    ├── summary.json              # Plant summary statistics  
    ├── plant_000/               # Individual plant data
    │   ├── crop.jpg             # Cropped plant image
    │   ├── highlight.jpg        # Analysis visualization
    │   └── data.json            # Plant telemetry & metadata
    └── plant_001/               # Additional plants...
```

### Legacy Compatibility Layer

```
/app/data/
├── plants/plant_000/            # New structure (zero-padded)
├── plant_0.json                # Legacy format (maintained for compatibility)
└── plant_0_crop.jpg            # Legacy images (maintained for compatibility)
```

## MQTT Topic Hierarchy

### Unified Namespace Structure (UNS)

```
plantvision/
├── {room}/                     # Physical location (room-1, greenhouse-a)
│   ├── {area}/                 # Subdivision within room (area-1, shelf-2)
│   │   ├── {camera_id}/        # Camera identifier (cam-0, cam-west)
│   │   │   ├── system/         # System-level telemetry
│   │   │   │   ├── status      # Camera/system status
│   │   │   │   ├── config      # Configuration changes
│   │   │   │   └── alerts      # System alerts & errors
│   │   │   ├── analysis/       # Combined analysis data
│   │   │   │   ├── summary     # Overall statistics
│   │   │   │   └── telemetry   # Main data payload  
│   │   │   ├── sprouts/        # Sprout-specific data
│   │   │   │   ├── {id}/       # Individual sprout
│   │   │   │   │   ├── telemetry
│   │   │   │   │   ├── alerts
│   │   │   │   │   └── status  
│   │   │   │   └── summary     # All sprouts summary
│   │   │   └── plants/         # Plant-specific data
│   │   │       ├── {id}/       # Individual plant
│   │   │       │   ├── telemetry
│   │   │       │   ├── alerts
│   │   │       │   └── status
│   │   │       └── summary     # All plants summary
```

### Example Topic Paths

```
# System Status
plantvision/greenhouse-a/shelf-1/cam-0/system/status

# Main Analysis Feed  
plantvision/greenhouse-a/shelf-1/cam-0/analysis/telemetry

# Individual Sprout
plantvision/greenhouse-a/shelf-1/cam-0/sprouts/0/telemetry

# Individual Plant
plantvision/greenhouse-a/shelf-1/cam-0/plants/2/telemetry

# Aggregate Data
plantvision/greenhouse-a/shelf-1/cam-0/sprouts/summary
plantvision/greenhouse-a/shelf-1/cam-0/plants/summary
```

## Data Schemas

### Sprout Telemetry Schema

```json
{
  "id": 0,
  "type": "sprout",
  "classification": "sprout", 
  "timestamp": 1757664390780,
  "growth_stage": 1,           // 0=cotyledon, 1=first_leaves, 2=early_vegetative
  "bbox": [625, 36, 101, 141],
  "area_pixels": 10346.5,
  "area_cm2": 2.8,
  "height_cm": 4.2,
  "width_cm": 3.8,
  "leaf_count": 4,
  "health_score": 87.5,
  "mean_bgr": [44.96, 126.04, 81.05],
  "label": "basil",
  "raw_image_base64": "...",
  "image_format": "jpg",
  "camera_info": {
    "room": "greenhouse-a",
    "area": "shelf-1", 
    "camera_id": "cam-0"
  }
}
```

### Plant Telemetry Schema  

```json
{
  "id": 2,
  "type": "plant",
  "classification": "plant",
  "timestamp": 1757664390780,
  "growth_stage": 3,           // 3=vegetative, 4=flowering, 5=fruiting
  "bbox": [450, 120, 280, 350],
  "area_pixels": 25680.3,
  "area_cm2": 15.7,
  "height_cm": 18.5,
  "width_cm": 12.3,
  "leaf_count": 28,
  "petal_count": 0,
  "bud_count": 3,
  "fruit_count": 0,
  "health_score": 92.1,
  "mean_bgr": [38.22, 142.18, 95.44],
  "label": "basil",
  "raw_image_base64": "...",
  "image_format": "jpg", 
  "camera_info": {
    "room": "greenhouse-a",
    "area": "shelf-1",
    "camera_id": "cam-0"
  },
  "disease_indicators": {
    "brown_spots": 2,
    "yellowing": 1,
    "wilting": 0
  }
}
```

### Summary Data Schema

```json
{
  "timestamp": 1757664390780,
  "camera_info": {
    "room": "greenhouse-a", 
    "area": "shelf-1",
    "camera_id": "cam-0"
  },
  "totals": {
    "sprout_count": 3,
    "plant_count": 2, 
    "total_instances": 5,
    "total_area_pixels": 87234.1,
    "total_area_cm2": 42.3
  },
  "health_summary": {
    "average_health": 89.2,
    "healthy_count": 4,
    "stressed_count": 1,
    "diseased_count": 0
  },
  "growth_distribution": {
    "cotyledon": 1,
    "first_leaves": 2, 
    "early_vegetative": 0,
    "vegetative": 2,
    "flowering": 0,
    "fruiting": 0
  }
}
```

## Migration Strategy

### Phase 1: Dual Structure Support
- Maintain legacy file structure for compatibility
- Implement new hierarchical structure in parallel  
- Update C++ to write to both formats

### Phase 2: Enhanced Processing
- Implement specialized sprout vs plant processing pipelines
- Add growth stage detection algorithms
- Implement health scoring improvements

### Phase 3: Legacy Deprecation  
- Phase out legacy flat structure
- Update all client applications to use new APIs
- Remove compatibility shims

## Performance Considerations

### File I/O Optimization
- Use atomic writes for data files 
- Implement file rotation for historical data
- Add compression for archived data

### MQTT Optimization  
- Use appropriate QoS levels (0 for telemetry, 1 for alerts)
- Implement retained messages for status topics
- Use topic filters for efficient subscriptions

### Storage Management
- Implement automatic cleanup of old image data
- Add configurable retention policies
- Compress historical telemetry data
