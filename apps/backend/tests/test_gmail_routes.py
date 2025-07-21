import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app
from app.core.auth import get_current_user

client = TestClient(app)


def mock_get_current_user():
    return {"user_id": "test_user"}


class TestGmailRoutes:
    
    def setup_method(self):
        app.dependency_overrides[get_current_user] = mock_get_current_user
    
    def teardown_method(self):
        app.dependency_overrides.clear()
    
    @patch('app.routes.gmail.gmail_service')
    def test_test_gmail_connection_success(self, mock_gmail_service):
        mock_gmail_service.create_gmail_client.return_value = True
        
        response = client.post(
            "/api/gmail/test-connection",
            json={
                "access_token": "test_token",
                "refresh_token": "test_refresh"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Gmail connection successful" in data["message"]
    
    @patch('app.routes.gmail.gmail_service')
    def test_setup_filter_success(self, mock_gmail_service):
        mock_gmail_service.create_gmail_client.return_value = True
        mock_gmail_service.setup_job_application_labeling.return_value = "Label_123"
        
        response = client.post(
            "/api/gmail/setup-filter",
            json={
                "credentials": {
                    "access_token": "test_token",
                    "refresh_token": "test_refresh"
                },
                "label_name": "Job Applications"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["label_id"] == "Label_123"
        assert "Successfully set up" in data["message"]
    
    @patch('app.routes.gmail.gmail_service')
    def test_setup_filter_auth_failure(self, mock_gmail_service):
        mock_gmail_service.create_gmail_client.return_value = False
        
        response = client.post(
            "/api/gmail/setup-filter",
            json={
                "credentials": {
                    "access_token": "invalid_token",
                    "refresh_token": "invalid_refresh"
                }
            }
        )
        
        assert response.status_code == 400
        assert "Failed to authenticate with Gmail API" in response.json()["detail"]
    
    @patch('app.routes.gmail.gmail_service')
    def test_list_filters_success(self, mock_gmail_service):
        mock_gmail_service.list_existing_filters.return_value = [
            {"id": "Filter_1", "criteria": {}},
            {"id": "Filter_2", "criteria": {}}
        ]
        
        response = client.get("/api/gmail/filters")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["filters"]) == 2
        assert data["count"] == 2
    
    @patch('app.routes.gmail.gmail_service')
    def test_delete_filter_success(self, mock_gmail_service):
        mock_gmail_service.delete_filter.return_value = True
        
        response = client.delete("/api/gmail/filters/Filter_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]
