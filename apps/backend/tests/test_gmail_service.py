import pytest
from unittest.mock import Mock, patch, MagicMock
from apps.backend.app.services.gmail_service import GmailService


class TestGmailService:
    
    def setup_method(self):
        self.gmail_service = GmailService()
    
    @patch('app.services.gmail.build')
    @patch('app.services.gmail.Credentials')
    def test_create_gmail_client_success(self, mock_credentials, mock_build):
        mock_creds = Mock()
        mock_creds.expired = False
        mock_credentials.return_value = mock_creds
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        user_credentials = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token"
        }
        
        result = self.gmail_service.create_gmail_client(user_credentials)
        
        assert result is True
        assert self.gmail_service.service == mock_service
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)
    
    @patch('app.services.gmail.build')
    @patch('app.services.gmail.Credentials')
    def test_create_gmail_client_with_refresh(self, mock_credentials, mock_build):
        mock_creds = Mock()
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"
        mock_credentials.return_value = mock_creds
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        user_credentials = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token"
        }
        
        with patch('app.services.gmail.Request') as mock_request:
            result = self.gmail_service.create_gmail_client(user_credentials)
        
        assert result is True
        mock_creds.refresh.assert_called_once()
    
    def test_get_or_create_label_existing(self):
        mock_service = Mock()
        mock_labels_list = Mock()
        mock_labels_list.list.return_value.execute.return_value = {
            "labels": [
                {"id": "Label_123", "name": "Job Applications"},
                {"id": "Label_456", "name": "Other Label"}
            ]
        }
        mock_service.users.return_value.labels.return_value = mock_labels_list
        
        self.gmail_service.service = mock_service
        
        result = self.gmail_service.get_or_create_label("Job Applications")
        
        assert result == "Label_123"
    
    def test_get_or_create_label_new(self):
        mock_service = Mock()
        mock_labels_list = Mock()
        mock_labels_list.list.return_value.execute.return_value = {
            "labels": []
        }
        mock_labels_create = Mock()
        mock_labels_create.create.return_value.execute.return_value = {
            "id": "Label_NewJobApps"
        }
        mock_labels_list.create = mock_labels_create.create
        mock_service.users.return_value.labels.return_value = mock_labels_list
        
        self.gmail_service.service = mock_service
        
        result = self.gmail_service.get_or_create_label("Job Applications")
        
        assert result == "Label_NewJobApps"
    
    def test_create_job_application_filter_success(self):
        mock_service = Mock()
        mock_filters = Mock()
        mock_filters.create.return_value.execute.return_value = {
            "id": "Filter_123"
        }
        mock_service.users.return_value.settings.return_value.filters.return_value = mock_filters
        
        self.gmail_service.service = mock_service
        
        result = self.gmail_service.create_job_application_filter("Label_123")
        
        assert result is True
        mock_filters.create.assert_called_once()
    
    def test_setup_job_application_labeling_complete(self):
        mock_service = Mock()
        
        # Mock label creation
        mock_labels_list = Mock()
        mock_labels_list.list.return_value.execute.return_value = {"labels": []}
        mock_labels_list.create.return_value.execute.return_value = {"id": "Label_123"}
        
        # Mock filter creation
        mock_filters = Mock()
        mock_filters.create.return_value.execute.return_value = {"id": "Filter_123"}
        
        mock_service.users.return_value.labels.return_value = mock_labels_list
        mock_service.users.return_value.settings.return_value.filters.return_value = mock_filters
        
        self.gmail_service.service = mock_service
        
        result = self.gmail_service.setup_job_application_labeling()
        
        assert result == "Label_123"
    
    def test_service_not_initialized(self):
        result = self.gmail_service.get_or_create_label()
        assert result is None
        
        result = self.gmail_service.create_job_application_filter("test_label_id")
        assert result is False
        
        result = self.gmail_service.setup_job_application_labeling()
        assert result is None
