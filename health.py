"""Health check and monitoring endpoints."""
import os
import psutil
from datetime import datetime
from typing import Dict, Any


def get_system_health() -> Dict[str, Any]:
    """
    Get system health metrics.
    
    Returns:
        Dictionary with health status and metrics
    """
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_mb = memory.available / (1024 * 1024)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_free_gb = disk.free / (1024 * 1024 * 1024)
        
        # Determine overall status
        status = "healthy"
        issues = []
        
        if cpu_percent > 90:
            status = "degraded"
            issues.append("High CPU usage")
        
        if memory_percent > 90:
            status = "degraded"
            issues.append("High memory usage")
        
        if disk_percent > 90:
            status = "degraded"
            issues.append("Low disk space")
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(datetime.now().timestamp() - psutil.boot_time()),
            "metrics": {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory_percent, 2),
                "memory_available_mb": round(memory_available_mb, 2),
                "disk_percent": round(disk_percent, 2),
                "disk_free_gb": round(disk_free_gb, 2),
            },
            "issues": issues
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


def check_ai_service() -> Dict[str, Any]:
    """
    Check AI service availability.
    
    Returns:
        Dictionary with AI service status
    """
    try:
        from ai_config import AIConfig
        
        api_key_configured = (
            AIConfig.GEMINI_API_KEY and 
            AIConfig.GEMINI_API_KEY != 'YOUR_API_KEY_HERE'
        )
        
        return {
            "enabled": AIConfig.AI_CHECKING_ENABLED,
            "api_key_configured": api_key_configured,
            "model": AIConfig.GEMINI_MODEL,
            "cache_enabled": AIConfig.CACHE_AI_RESPONSES,
            "status": "healthy" if (AIConfig.AI_CHECKING_ENABLED and api_key_configured) else "degraded"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def check_database() -> Dict[str, Any]:
    """
    Check database connectivity.
    
    Returns:
        Dictionary with database status
    """
    try:
        # Try to import cache manager
        from ai_cache import cache_manager
        
        # Simple connectivity test
        result = cache_manager.get_cached_result(
            student_answer="test",
            correct_variants=["test"],
            question_context="health_check",
            ai_model="test"
        )
        
        return {
            "status": "healthy",
            "type": "postgresql",
            "cache_available": True
        }
    except ImportError:
        return {
            "status": "degraded",
            "type": "none",
            "cache_available": False,
            "message": "Database cache not configured"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def check_file_system() -> Dict[str, Any]:
    """
    Check file system directories.
    
    Returns:
        Dictionary with file system status
    """
    from config import Config
    
    directories = {
        "uploads": Config.UPLOAD_FOLDER,
        "templates": Config.TEMPLATES_FOLDER,
        "credentials": Config.CREDENTIALS_FOLDER,
    }
    
    status = "healthy"
    issues = []
    
    for name, path in directories.items():
        if not os.path.exists(path):
            status = "degraded"
            issues.append(f"Missing directory: {name}")
        elif not os.access(path, os.W_OK):
            status = "degraded"
            issues.append(f"No write permission: {name}")
    
    return {
        "status": status,
        "directories": {
            name: {
                "exists": os.path.exists(path),
                "writable": os.access(path, os.W_OK) if os.path.exists(path) else False
            }
            for name, path in directories.items()
        },
        "issues": issues
    }


def get_application_info() -> Dict[str, Any]:
    """
    Get application information.
    
    Returns:
        Dictionary with application info
    """
    return {
        "name": "PDF Testing System",
        "version": "1.0.0",
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "environment": "development" if os.getenv("DEBUG", "False") == "True" else "production"
    }
