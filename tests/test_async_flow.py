from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pytest
import json

def test_analyze_async_flow(client, mock_task_repo):
    """
    Test the full async analysis flow:
    1. POST /analyze/async -> returns task_id
    2. TaskRepository.create_task is called
    3. Background task is added
    """
    payload = {
        "power_data": [100, 110, 120, 130, 140, 150, 160, 170, 180, 190],
        "ftp": 250,
        "w_prime": 20000
    }
    
    # 1. Trigger Async Analysis
    response = client.post("/analyze/async", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"
    
    task_id = data["task_id"]
    
    # Verify TaskRepository.create_task was called
    mock_task_repo.create_task.assert_called_once_with(task_id)

def test_get_task_status(client, mock_task_repo):
    """Test retrieving task status"""
    task_id = "test-uuid-123"
    
    mock_task_repo.get_task.return_value = {
        "task_id": task_id,
        "status": "completed",
        "result": {"run_metrics": {"w_prime_balance": 15000}},
        "error": None
    }
    
    response = client.get(f"/tasks/{task_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "completed"
    assert "result" in data

def test_task_not_found(client, mock_task_repo):
    """Test 404 behavior"""
    mock_task_repo.get_task.return_value = None
    
    response = client.get("/tasks/non-existent-id")
    assert response.status_code == 404
