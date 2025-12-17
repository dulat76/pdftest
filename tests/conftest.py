"""Test configuration and fixtures."""
import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def app():
    """Create Flask app for testing."""
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    return flask_app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_template_data():
    """Sample template data for testing."""
    return {
        "name": "Test Template",
        "template_id": "test_template_1",
        "fields": [
            {
                "id": "field1",
                "variants": ["answer1", "answer2"],
                "x": 100,
                "y": 100,
                "width": 200,
                "height": 30
            },
            {
                "id": "field2",
                "variants": ["correct"],
                "x": 100,
                "y": 150,
                "width": 200,
                "height": 30
            }
        ]
    }


@pytest.fixture
def sample_student_info():
    """Sample student information for testing."""
    return {
        "name": "Иванов Иван Иванович",
        "class": "10А"
    }


@pytest.fixture
def sample_answers():
    """Sample student answers for testing."""
    return {
        "field1": "answer1",
        "field2": "correct"
    }
