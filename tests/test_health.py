"""Unit tests for health check module."""
import pytest
from health import (
    get_system_health,
    check_ai_service,
    check_database,
    check_file_system,
    get_application_info,
)


class TestSystemHealth:
    """Tests for system health checks."""
    
    def test_get_system_health_returns_dict(self):
        """Test that get_system_health returns a dictionary."""
        result = get_system_health()
        assert isinstance(result, dict)
        assert "status" in result
        assert "timestamp" in result
    
    def test_system_health_has_metrics(self):
        """Test that system health includes metrics."""
        result = get_system_health()
        if result["status"] != "error":
            assert "metrics" in result
            assert "cpu_percent" in result["metrics"]
            assert "memory_percent" in result["metrics"]


class TestAIService:
    """Tests for AI service checks."""
    
    def test_check_ai_service_returns_dict(self):
        """Test that check_ai_service returns a dictionary."""
        result = check_ai_service()
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_ai_service_has_config(self):
        """Test that AI service check includes configuration."""
        result = check_ai_service()
        if result["status"] != "error":
            assert "enabled" in result
            assert "model" in result


class TestDatabase:
    """Tests for database checks."""
    
    def test_check_database_returns_dict(self):
        """Test that check_database returns a dictionary."""
        result = check_database()
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_database_status_valid(self):
        """Test that database status is valid."""
        result = check_database()
        assert result["status"] in ["healthy", "degraded", "error"]


class TestFileSystem:
    """Tests for file system checks."""
    
    def test_check_file_system_returns_dict(self):
        """Test that check_file_system returns a dictionary."""
        result = check_file_system()
        assert isinstance(result, dict)
        assert "status" in result
        assert "directories" in result
    
    def test_file_system_checks_directories(self):
        """Test that file system check includes directory status."""
        result = check_file_system()
        assert "uploads" in result["directories"]
        assert "templates" in result["directories"]


class TestApplicationInfo:
    """Tests for application information."""
    
    def test_get_application_info_returns_dict(self):
        """Test that get_application_info returns a dictionary."""
        result = get_application_info()
        assert isinstance(result, dict)
    
    def test_application_info_has_version(self):
        """Test that application info includes version."""
        result = get_application_info()
        assert "name" in result
        assert "version" in result
        assert "python_version" in result
