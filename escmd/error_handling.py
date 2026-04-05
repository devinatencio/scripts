"""
Standardized error handling for the esclient refactored architecture.

This module provides consistent error handling, logging, and response
formatting across all command processors and components.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union, Callable
from functools import wraps
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high" 
    CRITICAL = "critical"


class ESClientError(Exception):
    """Base exception for esclient operations."""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.context = context or {}


class ConnectionError(ESClientError):
    """Elasticsearch connection error."""
    
    def __init__(self, message: str, host: str, port: int, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorSeverity.HIGH, context)
        self.host = host
        self.port = port


class AuthenticationError(ESClientError):
    """Authentication/authorization error."""
    
    def __init__(self, message: str, username: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorSeverity.HIGH, context)
        self.username = username


class OperationError(ESClientError):
    """General operation error."""
    
    def __init__(self, message: str, operation: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message, severity, context)
        self.operation = operation


class ErrorHandler:
    """
    Centralized error handling for esclient operations.
    
    This class provides standardized error handling, logging, and
    response formatting for consistent error management.
    """
    
    def __init__(self, logger_name: str = "esclient"):
        self.logger = logging.getLogger(logger_name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logging configuration if not already configured."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def format_error_response(self, error: Exception, operation: str, 
                             context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Format an error into a standardized response structure.
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            context: Additional context information
            
        Returns:
            dict: Standardized error response
        """
        error_response = {
            "success": False,
            "error": {
                "message": str(error),
                "type": error.__class__.__name__,
                "operation": operation,
                "severity": getattr(error, 'severity', ErrorSeverity.MEDIUM).value
            }
        }
        
        if context:
            error_response["error"]["context"] = context
        
        if hasattr(error, 'context') and error.context:
            error_response["error"]["additional_context"] = error.context
        
        return error_response
    
    def log_error(self, error: Exception, operation: str, 
                  context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an error with appropriate level based on severity.
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            context: Additional context information
        """
        severity = getattr(error, 'severity', ErrorSeverity.MEDIUM)
        
        log_message = f"Operation '{operation}' failed: {str(error)}"
        if context:
            log_message += f" | Context: {context}"
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:  # LOW
            self.logger.info(log_message)
    
    def handle_elasticsearch_exception(self, error: Exception, operation: str,
                                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle Elasticsearch-specific exceptions.
        
        Args:
            error: Elasticsearch exception
            operation: Description of the operation
            context: Additional context
            
        Returns:
            dict: Standardized error response
        """
        from elasticsearch.exceptions import (
            ConnectionError as ESConnectionError,
            AuthenticationException,
            AuthorizationException,
            NotFoundError,
            RequestError,
            TransportError
        )
        
        if isinstance(error, (ESConnectionError, TransportError)):
            es_error = ConnectionError(
                f"Failed to connect to Elasticsearch: {str(error)}",
                host=context.get('host', 'unknown') if context else 'unknown',
                port=context.get('port', 9200) if context else 9200,
                context=context
            )
        elif isinstance(error, (AuthenticationException, AuthorizationException)):
            es_error = AuthenticationError(
                f"Authentication/Authorization failed: {str(error)}",
                username=context.get('username', 'unknown') if context else 'unknown',
                context=context
            )
        elif isinstance(error, NotFoundError):
            es_error = OperationError(
                f"Resource not found: {str(error)}",
                operation=operation,
                severity=ErrorSeverity.LOW,
                context=context
            )
        elif isinstance(error, RequestError):
            es_error = OperationError(
                f"Invalid request: {str(error)}",
                operation=operation,
                severity=ErrorSeverity.MEDIUM,
                context=context
            )
        else:
            es_error = OperationError(
                f"Elasticsearch error: {str(error)}",
                operation=operation,
                context=context
            )
        
        self.log_error(es_error, operation, context)
        return self.format_error_response(es_error, operation, context)


def handle_errors(operation: str, error_handler: Optional[ErrorHandler] = None,
                  return_none_on_error: bool = False):
    """
    Decorator for standardized error handling in command methods.
    
    Args:
        operation: Description of the operation for logging
        error_handler: Custom error handler instance
        return_none_on_error: Return None instead of error dict on failure
        
    Returns:
        Decorated method with error handling
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            handler = error_handler or ErrorHandler()
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Extract context from method arguments if available
                context = {}
                if args and hasattr(args[0], '__class__'):
                    context['class'] = args[0].__class__.__name__
                if kwargs:
                    # Include non-sensitive kwargs in context
                    safe_kwargs = {k: v for k, v in kwargs.items() 
                                 if not any(secret in k.lower() for secret in ['password', 'token', 'secret'])}
                    context['parameters'] = safe_kwargs
                
                error_response = handler.handle_elasticsearch_exception(e, operation, context)
                
                return None if return_none_on_error else error_response
        
        return wrapper
    return decorator


def safe_execute(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """
    Safely execute a function with standardized error handling.
    
    Args:
        func: Function to execute
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        dict: Result or error response
    """
    handler = ErrorHandler()
    
    try:
        result = func(*args, **kwargs)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        operation = getattr(func, '__name__', 'unknown_operation')
        return handler.handle_elasticsearch_exception(e, operation)


# Global error handler instance
default_error_handler = ErrorHandler()

# Convenience decorators
handle_es_errors = lambda op: handle_errors(op, default_error_handler)
handle_es_errors_safe = lambda op: handle_errors(op, default_error_handler, return_none_on_error=True)
