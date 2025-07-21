from abc import ABC, abstractmethod
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Base service class providing common functionality for all services."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize()
    
    @abstractmethod
    def _initialize(self) -> None:
        """Initialize the service. Override in subclasses."""
        pass
    
    def _log_operation(self, operation: str, details: Optional[str] = None) -> None:
        """Log service operations."""
        message = f"{operation}"
        if details:
            message += f": {details}"
        self.logger.info(message)
    
    def _log_error(self, operation: str, error: Exception) -> None:
        """Log service errors."""
        self.logger.error(f"Failed {operation}: {str(error)}")


class ServiceError(Exception):
    """Base exception for service operations."""
    pass


class ServiceInitializationError(ServiceError):
    """Exception raised when service initialization fails."""
    pass


class ServiceOperationError(ServiceError):
    """Exception raised when service operations fail."""
    pass
