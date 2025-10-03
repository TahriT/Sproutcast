# PlantVision Data Organization

This document describes the complete data organization structure for PlantVision, including filesystem layout, MQTT topic hierarchy, and data schemas for plants and sprouts.

## Directory Structure

### Production Data Layout

```
/app/data/
├── config.json                    # System configuration
├── frame_raw.jpg                  # Latest camera capture
├── frame_annotated.jpg           # Latest analysis with overlays
├── ai_metrics.json               # AI processing performance metrics
├── classes_overrides.json        # Manual classification corrections
├── setup_session.json            # Session initialization data
│
├── sprouts/                      # Early growth stage instances
│   ├── summary.json              # Aggregate sprout statistics
│   ├── sprout_000/              # Individual sprout (zero-padded IDs)
│   │   ├── data.json            # Sprout telemetry & metadata
│   │   ├── crop.jpg             # Cropped sprout image
│   │   └── highlight.jpg        # Analysis visualization
│   ├── sprout_001/
│   └── ...
│
├── plants/                       # Mature plant instances
│   ├── summary.json              # Aggregate plant statistics
│   ├── plant_000/               # Individual plant (zero-padded IDs)
│   │   ├── data.json            # Plant telemetry & metadata
│   │   ├── crop.jpg             # Cropped plant image
│   │   └── highlight.jpg        # Analysis visualization
│   ├── plant_001/
│   └── ...
│
├── ai_requests/                  # C++ → Python AI queue
│   ├── req_001.json             # AI request metadata
│   ├── frame_001.jpg            # Frame for AI processing
│   ├── ai_analysis_req_001.signal # Notification signal file
│   └── ...
│
├── ai_results/                   # Python → C++ AI responses
│   ├── req_001.json             # AI result metadata
│   ├── depth_req_001.npy        # Depth map (NumPy format)
│   └── ...
│
└── debug/                        # Debug output (optional, when enabled)
    ├── frame_000_mask.jpg
    ├── frame_000_contours.jpg
    ├── change_detection_000.jpg
    └── ...
```

### Legacy Compatibility

For backward compatibility, flat-file references are maintained:

```
/app/data/
├── plant_0.json → plants/plant_000/data.json
├── plant_0_crop.jpg → plants/plant_000/crop.jpg
├── plant_0_highlight.jpg → plants/plant_000/highlight.jpg
└── ...
```

**Note**: Legacy format is deprecated and will be removed in v2.0.

## Data Schemas

### Sprout Data Schema

**Location**: `sprouts/sprout_{id}/data.json`

```json
{
  "id": 0,
  "type": "sprout",
  "classification": "sprout",
  "timestamp": 1757664390780,
  "growth_stage": 1,
  "growth_stage_name": "first_leaves",
  "bbox": [625, 36, 101, 141],
  "area_pixels": 10346.5,
  "area_cm2": 2.8,
  "height_cm": 4.2,
  "width_cm": 3.8,
  "leaf_count": 4,
  "health_score": 87.5,
  "mean_bgr": [44.96, 126.04, 81.05],
  "mean_hsv": [35.2, 62.1, 126.04],
  "mean_lab": [52.3, -28.4, 42.1],
  "label": "basil",
  "confidence": 0.92,
  "raw_image_base64": "...",
  "image_format": "jpg",
  "camera_info": {
    "room": "greenhouse-a",
    "area": "shelf-1",
    "camera_id": "cam-0"
  },
  "processing_metadata": {
    "threshold_used": 100,
    "scale_px_per_cm": 28.0,
    "processing_time_ms": 45.2
  }
}
```

**Growth Stages** (0-2):
- `0`: cotyledon - Seed leaves only
- `1`: first_leaves - True leaves emerging
- `2`: early_vegetative - Multiple leaf pairs

**Key Metrics**:
- **Leaf Count**: Number of distinct leaf structures detected
- **Health Score**: 0-100 composite score based on color and shape
- **Growth Rate**: Calculated from historical data (not stored per frame)

### Plant Data Schema

**Location**: `plants/plant_{id}/data.json`

```json
{
  "id": 2,
  "type": "plant",
  "classification": "plant",
  "timestamp": 1757664390780,
  "growth_stage": 3,
  "growth_stage_name": "vegetative",
  "bbox": [450, 120, 280, 350],
  "area_pixels": 25680.3,
  "area_cm2": 15.7,
  "height_cm": 18.5,
  "width_cm": 12.3,
  "leaf_count": 28,
  "petal_count": 0,
  "petal_area_cm2": 0.0,
  "bud_count": 3,
  "fruit_count": 0,
  "stem_length_cm": 12.4,
  "branch_count": 4,
  "health_score": 92.1,
  "health_status": "healthy",
  "mean_bgr": [38.22, 142.18, 95.44],
  "mean_hsv": [28.4, 68.3, 142.18],
  "mean_lab": [58.1, -32.7, 48.3],
  "solidity": 0.87,
  "eccentricity": 0.72,
  "circularity": 0.64,
  "label": "basil",
  "confidence": 0.95,
  "raw_image_base64": "...",
  "image_format": "jpg",
  "camera_info": {
    "room": "greenhouse-a",
    "area": "shelf-1",
    "camera_id": "cam-0"
  },
  "disease_indicators": {
    "brown_spots": 2,
    "brown_spot_percentage": 1.2,
    "yellowing": 1,
    "yellowing_percentage": 0.8,
    "wilting": 0
  },
  "stress_indicators": {
    "color_abnormality": false,
    "shape_abnormality": false,
    "growth_stunted": false
  },
  "morphology": {
    "compactness": 0.78,
    "aspect_ratio": 1.25,
    "form_factor": 0.64,
    "contour_complexity": 142.5
  },
  "processing_metadata": {
    "threshold_used": 100,
    "scale_px_per_cm": 28.0,
    "processing_time_ms": 78.4
  }
}
```

**Growth Stages** (3-5):
- `3`: vegetative - Active leaf development
- `4`: flowering - Buds/flowers present
- `5`: fruiting - Fruits/seeds developing

**Key Metrics**:
- **Morphology**: Shape descriptors for plant structure analysis
- **Disease Indicators**: Specific pathology detection counts
- **Stress Indicators**: Environmental stress markers
- **Health Status**: Categorical assessment (healthy, stressed, diseased, pest-damaged)

### Summary Data Schema

**Location**: `{plants|sprouts}/summary.json`

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
    "diseased_count": 0,
    "pest_damaged_count": 0
  },
  "growth_distribution": {
    "cotyledon": 1,
    "first_leaves": 2,
    "early_vegetative": 0,
    "vegetative": 2,
    "flowering": 0,
    "fruiting": 0
  },
  "species_distribution": {
    "basil": 3,
    "tomato": 1,
    "unknown": 1
  }
}
```

## MQTT Topic Hierarchy

### Unified Namespace Structure (UNS)

PlantVision implements a hierarchical MQTT topic structure following the Unified Namespace (UNS) pattern for industrial IoT:

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

### Topic Examples

```
# System Status
plantvision/greenhouse-a/shelf-1/cam-0/system/status
plantvision/greenhouse-a/shelf-1/cam-0/system/alerts

# Main Analysis Feed
plantvision/greenhouse-a/shelf-1/cam-0/analysis/telemetry
plantvision/greenhouse-a/shelf-1/cam-0/analysis/summary

# Individual Sprouts
plantvision/greenhouse-a/shelf-1/cam-0/sprouts/0/telemetry
plantvision/greenhouse-a/shelf-1/cam-0/sprouts/1/telemetry

# Individual Plants
plantvision/greenhouse-a/shelf-1/cam-0/plants/0/telemetry
plantvision/greenhouse-a/shelf-1/cam-0/plants/2/telemetry

# Aggregate Data
plantvision/greenhouse-a/shelf-1/cam-0/sprouts/summary
plantvision/greenhouse-a/shelf-1/cam-0/plants/summary
```

### MQTT Message Formats

#### System Status Message

**Topic**: `plantvision/{room}/{area}/{camera}/system/status`

```json
{
  "timestamp": 1757664390780,
  "status": "online",
  "uptime_seconds": 3600,
  "frame_rate_fps": 29.8,
  "processing_latency_ms": 65.2,
  "camera_info": {
    "room": "greenhouse-a",
    "area": "shelf-1",
    "camera_id": "cam-0"
  },
  "resource_usage": {
    "cpu_percent": 45.2,
    "memory_mb": 512.3
  }
}
```

#### Individual Telemetry Message

**Topic**: `plantvision/{room}/{area}/{camera}/{plants|sprouts}/{id}/telemetry`

Payload matches the respective data.json schema (see above).

#### Summary Message

**Topic**: `plantvision/{room}/{area}/{camera}/{plants|sprouts}/summary`

Payload matches the summary.json schema (see above).

#### Alert Message

**Topic**: `plantvision/{room}/{area}/{camera}/system/alerts`

```json
{
  "timestamp": 1757664390780,
  "severity": "warning",
  "category": "health",
  "message": "Plant 3 health score dropped below 50",
  "instance_id": 3,
  "instance_type": "plant",
  "camera_info": {
    "room": "greenhouse-a",
    "area": "shelf-1",
    "camera_id": "cam-0"
  }
}
```

### MQTT QoS Levels

| Topic Pattern | QoS | Retained | Rationale |
|---------------|-----|----------|-----------|
| `*/system/status` | 1 | Yes | Ensure status delivery |
| `*/telemetry` | 0 | No | High-frequency, loss acceptable |
| `*/summary` | 1 | Yes | Important aggregate data |
| `*/alerts` | 1 | No | Ensure alert delivery |
| `*/config` | 2 | Yes | Critical configuration changes |

### Subscription Patterns

```bash
# Monitor all sprouts across all cameras
mosquitto_sub -h localhost -t "plantvision/+/+/+/sprouts/+/telemetry"

# Monitor specific room
mosquitto_sub -h localhost -t "plantvision/greenhouse-a/#"

# Monitor all health alerts
mosquitto_sub -h localhost -t "plantvision/+/+/+/system/alerts"

# Get all summary data
mosquitto_sub -h localhost -t "plantvision/+/+/+/*/summary"
```

## Configuration Management

### System Configuration

**Location**: `/app/data/config.json`

```json
{
  "mqtt": {
    "host": "mqtt-broker",
    "port": 1883,
    "keepalive": 60,
    "qos": 1
  },
  "uns": {
    "room": "greenhouse-a",
    "area": "shelf-1",
    "camera_id": "cam-0",
    "plant_id": "plant-1"
  },
  "processing": {
    "threshold": 100,
    "publish_interval_ms": 1000,
    "scale_px_per_cm": 28.0,
    "input_mode": "IMAGE",
    "input_path": "/samples/plant.jpg",
    "enable_ai_depth": true,
    "ai_model_preference": "dpt_swin2"
  },
  "classification": {
    "sprout_max_area_px": 5000,
    "sprout_max_height_cm": 8.0,
    "confidence_threshold": 0.7
  },
  "cameras": [
    {
      "id": "cam-0",
      "enabled": true,
      "room": "greenhouse-a",
      "area": "shelf-1",
      "threshold": 100,
      "scale_px_per_cm": 28.0
    }
  ]
}
```

### Classes Override

**Location**: `/app/data/classes_overrides.json`

Manual corrections for misclassified plants:

```json
{
  "plant_0": "tomato",
  "plant_5": "basil",
  "sprout_2": "lettuce"
}
```

## Data Retention & Cleanup

### Retention Policies

| Data Type | Retention Period | Cleanup Strategy |
|-----------|------------------|------------------|
| Frame images | 24 hours | Rolling deletion |
| Instance JSON | 7 days | Archive to cold storage |
| Crop images | 7 days | Compressed archive |
| AI requests | 1 hour | Auto-delete after processing |
| AI results | 24 hours | Archive depth maps |
| Debug images | 1 hour | Disabled in production |

### Automated Cleanup

```bash
# Example cleanup script (run daily)
find /app/data/debug -type f -mtime +0 -delete
find /app/data/ai_requests -type f -mtime +0 -delete
find /app/data/ai_results -type f -mtime +1 -delete
```

## Performance Considerations

### File I/O Optimization

- **Atomic Writes**: Use temporary files with rename for data.json updates
- **Buffered I/O**: Minimize disk sync operations
- **Compression**: gzip for archived JSON data
- **Batch Operations**: Group file operations where possible

### MQTT Optimization

- **Payload Size**: Keep telemetry messages <10KB
- **Publish Rate**: Limit to configured interval (default 1Hz)
- **Topic Filters**: Use specific subscriptions vs. wildcards
- **Persistent Sessions**: For reliable telemetry collection

### Storage Management

```bash
# Expected storage usage (per camera, 24h retention)
Frame images:      ~2GB (1080p @ 1fps)
Instance data:     ~50MB (JSON + crops)
AI processing:     ~100MB (temporary)
Debug (if enabled): ~500MB
Total:             ~2.7GB per camera per day
```

## Migration Strategy

### From Legacy to Hierarchical Structure

**Phase 1: Dual Structure** (Current)
- Maintain both flat and hierarchical structures
- Legacy symlinks for compatibility
- Applications can use either format

**Phase 2: Deprecation Warning** (v1.5)
- Add deprecation warnings to legacy endpoints
- Update documentation to show new structure only
- Provide migration tools

**Phase 3: Legacy Removal** (v2.0)
- Remove flat-file structure
- Remove compatibility symlinks
- Breaking change release

### Migration Script

```bash
#!/bin/bash
# migrate_to_hierarchical.sh

DATA_DIR="/app/data"

# Migrate plants
for json in $DATA_DIR/plant_*.json; do
    id=$(basename "$json" .json | sed 's/plant_//')
    padded=$(printf "plant_%03d" "$id")
    mkdir -p "$DATA_DIR/plants/$padded"
    mv "$json" "$DATA_DIR/plants/$padded/data.json"
    mv "$DATA_DIR/plant_${id}_crop.jpg" "$DATA_DIR/plants/$padded/crop.jpg" 2>/dev/null
    mv "$DATA_DIR/plant_${id}_highlight.jpg" "$DATA_DIR/plants/$padded/highlight.jpg" 2>/dev/null
done

# Migrate sprouts (similar pattern)
# ...

echo "Migration complete!"
```

## Troubleshooting

### Common Issues

**1. Missing data.json files**
```bash
# Check for recent writes
ls -lt /app/data/plants/*/data.json | head -10

# Verify C++ app is running
docker ps | grep cpp-app

# Check for errors
docker logs sc-cpp | grep -i error
```

**2. MQTT topics not updating**
```bash
# Test MQTT connectivity
mosquitto_sub -h localhost -t "plantvision/#" -v

# Check MQTT broker
docker logs sc-mqtt | tail -50

# Verify configuration
cat /app/data/config.json | jq '.mqtt'
```

**3. Storage space issues**
```bash
# Check disk usage
du -sh /app/data/*

# Clean up old data
find /app/data -name "*.jpg" -mtime +7 -delete
find /app/data -name "*.json" -mtime +30 -delete
```

---

**Last Updated**: October 2, 2025
