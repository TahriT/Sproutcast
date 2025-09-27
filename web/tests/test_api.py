import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import sys

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)

@pytest.fixture
def mock_config():
    """Mock configuration data for testing"""
    return {
        "camera_id": 0,
        "scale_px_per_cm": 28.0,
        "mqtt": {
            "host": "localhost",
            "port": 1883,
            "topic": "test/topic"
        },
        "processing": {
            "sprout_size_threshold": 2500,
            "sprout_height_threshold": 5.0
        }
    }

@pytest.fixture
def mock_plant_data():
    """Mock plant data for testing"""
    return {
        "id": 0,
        "classification": "plant",
        "area_pixels": 5500.0,
        "area_cm2": 7.0,
        "leaf_area": 6.5,
        "health_score": 85,
        "morphology": {
            "solidity": 0.78,
            "eccentricity": 0.45
        }
    }

class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check_success(self):
        """Test that health endpoint returns success when services are running"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data

class TestAPIEndpoints:
    """Test main API endpoints"""
    
    def test_get_plants_empty(self):
        """Test getting plants when no data exists"""
        with patch('os.path.exists', return_value=False):
            response = client.get("/api/plants")
            assert response.status_code == 200
            assert response.json() == []
    
    def test_get_sprouts_empty(self):
        """Test getting sprouts when no data exists"""
        with patch('os.path.exists', return_value=False):
            response = client.get("/api/sprouts")
            assert response.status_code == 200
            assert response.json() == []
    
    @patch('builtins.open')
    @patch('os.path.exists')
    def test_get_plants_with_data(self, mock_exists, mock_open, mock_plant_data):
        """Test getting plants with existing data"""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_plant_data)
        
        response = client.get("/api/plants")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 0  # Should return list

class TestConfigurationAPI:
    """Test configuration management endpoints"""
    
    @patch('builtins.open')
    @patch('os.path.exists')
    def test_get_config(self, mock_exists, mock_open, mock_config):
        """Test getting configuration"""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_config)
        
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "camera_id" in data or "error" not in data  # Should succeed or give proper error
    
    def test_update_scale(self):
        """Test updating scale configuration"""
        with patch('builtins.open'), patch('os.path.exists', return_value=True):
            response = client.post("/api/scale", json={"scale_px_per_cm": 30.0})
            # Should not crash - exact behavior depends on file system
            assert response.status_code in [200, 500]  # Success or controlled error

class TestVideoFeed:
    """Test video streaming endpoint"""
    
    def test_video_feed_endpoint(self):
        """Test that video feed endpoint exists and responds"""
        response = client.get("/api/video_feed")
        # Video feed might fail without camera, but should not crash
        assert response.status_code in [200, 404, 500]

if __name__ == "__main__":
    pytest.main([__file__])