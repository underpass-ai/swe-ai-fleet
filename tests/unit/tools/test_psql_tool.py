"""Tests for psql tool."""

import pytest
from unittest.mock import patch, Mock
from core.tools.psql_tool import psql_exec


class TestPsqlTool:
    """Test cases for psql tool."""

    @patch('core.tools.psql_tool.subprocess.run')
    def test_psql_exec_success(self, mock_run):
        """Test psql_exec with successful execution."""
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "SELECT 1\n(1 row)"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc
        
        result = psql_exec("postgresql://user:pass@localhost:5432/db", "SELECT 1")
        
        assert result == (True, "SELECT 1\n(1 row)")
        mock_run.assert_called_once_with(
            ["psql", "postgresql://user:pass@localhost:5432/db", "-c", "SELECT 1"],
            capture_output=True,
            text=True
        )

    @patch('core.tools.psql_tool.subprocess.run')
    def test_psql_exec_failure(self, mock_run):
        """Test psql_exec with failed execution."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: syntax error at or near 'INVALID'"
        mock_run.return_value = mock_proc
        
        result = psql_exec("postgresql://user:pass@localhost:5432/db", "INVALID SQL")
        
        assert result == (False, "Error: syntax error at or near 'INVALID'")
        mock_run.assert_called_once_with(
            ["psql", "postgresql://user:pass@localhost:5432/db", "-c", "INVALID SQL"],
            capture_output=True,
            text=True
        )

    @patch('core.tools.psql_tool.subprocess.run')
    def test_psql_exec_connection_error(self, mock_run):
        """Test psql_exec with connection error."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: connection to server failed"
        mock_run.return_value = mock_proc
        
        result = psql_exec("postgresql://user:pass@nonexistent:5432/db", "SELECT 1")
        
        assert result == (False, "Error: connection to server failed")
        mock_run.assert_called_once_with(
            ["psql", "postgresql://user:pass@nonexistent:5432/db", "-c", "SELECT 1"],
            capture_output=True,
            text=True
        )

    @patch('core.tools.psql_tool.subprocess.run')
    def test_psql_exec_with_warnings(self, mock_run):
        """Test psql_exec with warnings in output."""
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "CREATE TABLE\nCREATE TABLE"
        mock_proc.stderr = "Warning: table already exists"
        mock_run.return_value = mock_proc
        
        result = psql_exec("postgresql://user:pass@localhost:5432/db", "CREATE TABLE test (id INT)")
        
        assert result == (True, "CREATE TABLE\nCREATE TABLEWarning: table already exists")
        mock_run.assert_called_once_with(
            ["psql", "postgresql://user:pass@localhost:5432/db", "-c", "CREATE TABLE test (id INT)"],
            capture_output=True,
            text=True
        )

    @patch('core.tools.psql_tool.subprocess.run')
    def test_psql_exec_empty_connection_string(self, mock_run):
        """Test psql_exec with empty connection string."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: connection string is required"
        mock_run.return_value = mock_proc
        
        result = psql_exec("", "SELECT 1")
        
        assert result == (False, "Error: connection string is required")
        mock_run.assert_called_once_with(
            ["psql", "", "-c", "SELECT 1"],
            capture_output=True,
            text=True
        )

    @patch('core.tools.psql_tool.subprocess.run')
    def test_psql_exec_empty_sql(self, mock_run):
        """Test psql_exec with empty SQL command."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: SQL command is required"
        mock_run.return_value = mock_proc
        
        result = psql_exec("postgresql://user:pass@localhost:5432/db", "")
        
        assert result == (False, "Error: SQL command is required")
        mock_run.assert_called_once_with(
            ["psql", "postgresql://user:pass@localhost:5432/db", "-c", ""],
            capture_output=True,
            text=True
        )

    @patch('core.tools.psql_tool.subprocess.run')
    def test_psql_exec_authentication_error(self, mock_run):
        """Test psql_exec with authentication error."""
        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Error: authentication failed"
        mock_run.return_value = mock_proc
        
        result = psql_exec("postgresql://wronguser:wrongpass@localhost:5432/db", "SELECT 1")
        
        assert result == (False, "Error: authentication failed")
        mock_run.assert_called_once_with(
            ["psql", "postgresql://wronguser:wrongpass@localhost:5432/db", "-c", "SELECT 1"],
            capture_output=True,
            text=True
        )

    @patch('core.tools.psql_tool.subprocess.run')
    def test_psql_exec_subprocess_exception(self, mock_run):
        """Test psql_exec when subprocess raises an exception."""
        mock_run.side_effect = FileNotFoundError("psql command not found")
        
        with pytest.raises(FileNotFoundError):
            psql_exec("postgresql://user:pass@localhost:5432/db", "SELECT 1")

    def test_psql_exec_return_type(self):
        """Test that psql_exec returns correct types."""
        with patch('core.tools.psql_tool.subprocess.run') as mock_run:
            mock_proc = Mock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Success"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc
            
            result = psql_exec("postgresql://user:pass@localhost:5432/db", "SELECT 1")
            
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], bool)
            assert isinstance(result[1], str)

    @patch('core.tools.psql_tool.subprocess.run')
    def test_psql_exec_multiline_sql(self, mock_run):
        """Test psql_exec with multiline SQL command."""
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "CREATE TABLE\nINSERT 0 1"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc
        
        multiline_sql = "CREATE TABLE test (id INT); INSERT INTO test VALUES (1);"
        result = psql_exec("postgresql://user:pass@localhost:5432/db", multiline_sql)
        
        assert result == (True, "CREATE TABLE\nINSERT 0 1")
        mock_run.assert_called_once_with(
            ["psql", "postgresql://user:pass@localhost:5432/db", "-c", multiline_sql],
            capture_output=True,
            text=True
        )
