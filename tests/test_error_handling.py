import pytest
from datetime import datetime, timedelta
from larrybot.storage.task_repository import TaskRepository
from larrybot.models.task import Task
from unittest.mock import MagicMock, patch
from larrybot.core.exceptions import (
    LarryBotException, ValidationError, DatabaseError, NetworkError,
    AuthenticationError, FileError, PluginError, ServiceError, ErrorCode
)

class TestErrorHandling:
    """Test error handling in task operations."""

    def test_error_handling(self, test_session, db_task_factory):
        """Test error handling for invalid operations."""
        repo = TaskRepository(test_session)
        
        # Test updating non-existent task
        result = repo.update_priority(999, "High")
        assert result is None
        
        result = repo.update_status(999, "Done")
        assert result is None
        
        result = repo.update_due_date(999, datetime.utcnow())
        assert result is None
        
        # Test time tracking on non-existent task
        success = repo.start_time_tracking(999)
        assert not success
        
        duration = repo.stop_time_tracking(999)
        assert duration is None
        
        # Test adding self-dependency (should fail)
        task = db_task_factory(description="Test task")
        task_id = task.id
        success = repo.add_task_dependency(task_id, task_id)
        assert not success
        
        # Test adding duplicate dependency (should fail)
        task2 = db_task_factory(description="Test task 2")
        task2_id = task2.id
        success = repo.add_task_dependency(task_id, task2_id)
        assert success  # First dependency should succeed
        
        success = repo.add_task_dependency(task_id, task2_id)  # Duplicate
        assert not success
        
        # Test getting dependencies for non-existent task
        deps = repo.get_task_dependencies(999)
        assert len(deps) == 0
        
        # Test adding comment to non-existent task
        comment = repo.add_comment(999, "Test comment")
        assert comment is None
        
        # Test getting comments for non-existent task
        comments = repo.get_comments(999)
        assert len(comments) == 0
        
        # Test adding tags to non-existent task
        result = repo.add_tags(999, ["test"])
        assert result is None
        
        # Test removing tags from non-existent task
        result = repo.remove_tags(999, ["test"])
        assert result is None
        
        # Test getting tasks by non-existent tag
        tasks = repo.get_tasks_by_tag("non-existent-tag")
        assert len(tasks) == 0
        
        # Test getting tasks by non-existent category
        tasks = repo.get_tasks_by_category("NonExistentCategory")
        assert len(tasks) == 0
        
        # Test getting tasks by non-existent priority
        tasks = repo.get_tasks_by_priority("NonExistentPriority")
        assert len(tasks) == 0
        
        # Test getting tasks by non-existent status
        tasks = repo.get_tasks_by_status("NonExistentStatus")
        assert len(tasks) == 0

    def test_larrybot_exception_creation(self):
        """Test LarryBotException creation with different error codes."""
        # Test with different error codes
        error_codes = [
            ErrorCode.VALIDATION_ERROR,
            ErrorCode.DATABASE_ERROR,
            ErrorCode.NETWORK_ERROR,
            ErrorCode.AUTH_ERROR,
            ErrorCode.FILE_ERROR,
            ErrorCode.PLUGIN_ERROR,
            ErrorCode.SERVICE_ERROR
        ]
        
        for error_code in error_codes:
            exception = LarryBotException(
                message="Test error",
                error_code=error_code,
                context={"test": "data"}
            )
            assert exception.message == "Test error"
            assert exception.error_code == error_code
            assert exception.context == {"test": "data"}

    def test_larrybot_exception_user_message_generation(self):
        """Test user-friendly message generation for different error codes."""
        test_cases = [
            (ErrorCode.VALIDATION_ERROR, "The provided information is invalid"),
            (ErrorCode.DATABASE_ERROR, "We're experiencing database issues"),
            (ErrorCode.NETWORK_ERROR, "Network connection problem"),
            (ErrorCode.AUTH_ERROR, "Authentication failed"),
            (ErrorCode.FILE_ERROR, "File operation failed"),
            (ErrorCode.PLUGIN_ERROR, "Plugin error occurred"),
            (ErrorCode.SERVICE_ERROR, "Service temporarily unavailable")
        ]
        
        for error_code, expected_message in test_cases:
            exception = LarryBotException(
                message="Technical error",
                error_code=error_code
            )
            user_message = exception._generate_user_message()
            assert expected_message in user_message

    def test_larrybot_exception_unknown_error_code(self):
        """Test handling of unknown error codes."""
        exception = LarryBotException(
            message="Unknown error",
            error_code="UNKNOWN_CODE"
        )
        user_message = exception._generate_user_message()
        assert "An unexpected error occurred" in user_message

    def test_larrybot_exception_str_representation(self):
        """Test string representation of LarryBotException."""
        exception = LarryBotException(
            message="Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            context={"field": "value"}
        )
        
        str_repr = str(exception)
        assert "Test error" in str_repr
        # The string representation should contain the message
        assert "Test error" in str_repr

    def test_larrybot_exception_repr_representation(self):
        """Test repr representation of LarryBotException."""
        exception = LarryBotException(
            message="Test error",
            error_code=ErrorCode.DATABASE_ERROR
        )
        
        repr_str = repr(exception)
        assert "LarryBotException" in repr_str
        assert "Test error" in repr_str

    def test_specific_exception_types(self):
        """Test specific exception types inherit from LarryBotException."""
        # Test ValidationError
        validation_error = ValidationError("Invalid input")
        assert isinstance(validation_error, LarryBotException)
        assert validation_error.error_code == ErrorCode.VALIDATION_ERROR
        
        # Test DatabaseError
        db_error = DatabaseError("Database connection failed")
        assert isinstance(db_error, LarryBotException)
        assert db_error.error_code == ErrorCode.DATABASE_ERROR
        
        # Test NetworkError
        network_error = NetworkError("Connection timeout")
        assert isinstance(network_error, LarryBotException)
        assert network_error.error_code == ErrorCode.NETWORK_ERROR
        
        # Test AuthenticationError
        auth_error = AuthenticationError("Invalid credentials")
        assert isinstance(auth_error, LarryBotException)
        assert auth_error.error_code == ErrorCode.AUTH_ERROR
        
        # Test FileError
        file_error = FileError("File not found")
        assert isinstance(file_error, LarryBotException)
        assert file_error.error_code == ErrorCode.FILE_ERROR
        
        # Test PluginError
        plugin_error = PluginError("Plugin initialization failed")
        assert isinstance(plugin_error, LarryBotException)
        assert plugin_error.error_code == ErrorCode.PLUGIN_ERROR
        
        # Test ServiceError
        service_error = ServiceError("Service unavailable")
        assert isinstance(service_error, LarryBotException)
        assert service_error.error_code == ErrorCode.SERVICE_ERROR

    def test_exception_with_details(self):
        """Test exception creation with detailed information."""
        exception = ValidationError(
            message="Email validation failed",
            field_name="email",
            invalid_value="invalid@"
        )
        
        assert exception.context["field_name"] == "email"
        assert exception.context["invalid_value"] == "invalid@"
        assert "Email validation failed" in str(exception)

    def test_exception_with_context(self):
        """Test exception creation with context information."""
        context = {
            "operation": "user_registration",
            "user_id": 12345,
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        exception = DatabaseError(
            message="User creation failed",
            context=context
        )
        
        assert exception.context == context

    def test_exception_chaining(self):
        """Test exception chaining with original exception."""
        original_error = ValueError("Original error")
        larrybot_error = DatabaseError(
            message="Database operation failed",
            original_exception=original_error
        )
        
        assert larrybot_error.original_exception == original_error

    def test_error_code_enum_values(self):
        """Test ErrorCode enum values."""
        assert ErrorCode.VALIDATION_ERROR.value == "V001"
        assert ErrorCode.DATABASE_ERROR.value == "D001"
        assert ErrorCode.NETWORK_ERROR.value == "N001"
        assert ErrorCode.AUTH_ERROR.value == "A001"
        assert ErrorCode.FILE_ERROR.value == "F001"
        assert ErrorCode.PLUGIN_ERROR.value == "P001"
        assert ErrorCode.SERVICE_ERROR.value == "S001"

    def test_exception_logging_integration(self):
        """Test exception integration with logging."""
        with patch('larrybot.core.exceptions.logger') as mock_logger:
            exception = LarryBotException(
                message="Test error for logging",
                error_code=ErrorCode.VALIDATION_ERROR
            )
            
            # Simulate logging the exception
            mock_logger.error.assert_not_called()  # No automatic logging
            
            # Test that exception can be logged
            mock_logger.error(str(exception))
            mock_logger.error.assert_called_once()

    def test_exception_serialization(self):
        """Test exception serialization for API responses."""
        exception = LarryBotException(
            message="API error",
            error_code=ErrorCode.SERVICE_ERROR,
            context={"endpoint": "/api/tasks"}
        )
        
        # Test that exception can be converted to dict-like structure
        error_dict = exception.to_dict()
        
        assert error_dict["message"] == "API error"
        assert error_dict["error_code"] == "S001"
        assert error_dict["context"]["endpoint"] == "/api/tasks"

    def test_exception_recovery_scenarios(self):
        """Test exception recovery scenarios."""
        # Test validation error recovery
        validation_error = ValidationError("Invalid input")
        user_message = validation_error._generate_user_message()
        assert "check your input" in user_message.lower()
        
        # Test database error recovery
        db_error = DatabaseError("Connection lost")
        user_message = db_error._generate_user_message()
        assert "try again" in user_message.lower()
        
        # Test network error recovery
        network_error = NetworkError("Timeout")
        user_message = network_error._generate_user_message()
        assert "check your connection" in user_message.lower()

    def test_exception_edge_cases(self):
        """Test exception edge cases."""
        # Test with empty message
        exception = LarryBotException("", ErrorCode.VALIDATION_ERROR)
        assert exception.message == ""
        
        # Test with None context
        exception = LarryBotException("Test", ErrorCode.VALIDATION_ERROR, context=None)
        assert exception.context == {}
        
        # Test with empty context
        exception = LarryBotException("Test", ErrorCode.VALIDATION_ERROR, context={})
        assert exception.context == {}

    def test_exception_inheritance_hierarchy(self):
        """Test exception inheritance hierarchy."""
        # All specific exceptions should inherit from LarryBotException
        exceptions = [
            ValidationError("test"),
            DatabaseError("test"),
            NetworkError("test"),
            AuthenticationError("test"),
            FileError("test"),
            PluginError("test"),
            ServiceError("test")
        ]
        
        for exception in exceptions:
            assert isinstance(exception, LarryBotException)
            assert isinstance(exception, Exception)

    def test_exception_error_code_consistency(self):
        """Test that error codes are consistent across exception types."""
        error_code_mapping = {
            ValidationError: ErrorCode.VALIDATION_ERROR,
            DatabaseError: ErrorCode.DATABASE_ERROR,
            NetworkError: ErrorCode.NETWORK_ERROR,
            AuthenticationError: ErrorCode.AUTH_ERROR,
            FileError: ErrorCode.FILE_ERROR,
            PluginError: ErrorCode.PLUGIN_ERROR,
            ServiceError: ErrorCode.SERVICE_ERROR
        }
        
        for exception_class, expected_code in error_code_mapping.items():
            exception = exception_class("Test message")
            assert exception.error_code == expected_code 