import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Add parent directory to path so we can import 'main'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, TaskRepository

@pytest.fixture
def client():
    """Client for testing endpoints"""
    return TestClient(app)

@pytest.fixture
def mock_db_cursor():
    """Mock database cursor"""
    cursor = MagicMock()
    # Mock fetching task
    cursor.fetchone.return_value = (
        'test-task-id', 'pending', None, None, datetime.now(), datetime.now()
    )
    return cursor

@pytest.fixture
def mock_db_connection(mock_db_cursor):
    """Mock database connection"""
    conn = MagicMock()
    conn.cursor.return_value = mock_db_cursor
    return conn

@pytest.fixture
def override_db(mock_db_connection):
    """Override get_db_connection in main to use mock"""
    with patch('main.get_db_connection', return_value=mock_db_connection):
        yield mock_db_connection

@pytest.fixture
def mock_task_repo():
    """Mock TaskRepository for isolated testing"""
    with patch('main.TaskRepository') as mock:
        yield mock

from datetime import datetime
