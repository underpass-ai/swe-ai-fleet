"""Process executor for running commands."""

import subprocess

from core.agents_and_tools.tools.domain.process_command import ProcessCommand
from core.agents_and_tools.tools.domain.process_result import ProcessResult


def execute_process(command: ProcessCommand, raise_on_error: bool | None = None) -> ProcessResult:
    """
    Execute a process command and return result entity.
    
    Following DDD principles:
    - Accepts value object (ProcessCommand)
    - Returns entity (ProcessResult)
    - Encapsulates subprocess complexity
    
    Args:
        command: The command to execute
        raise_on_error: If True, raise on non-zero exit (overrides command.check_returncode)
    
    Returns:
        ProcessResult entity with execution result
        
    Raises:
        subprocess.CalledProcessError: If raise_on_error is True and command fails
        subprocess.TimeoutExpired: If command exceeds timeout
        FileNotFoundError: If command program not found
    
    Examples:
        # Simple execution
        cmd = ProcessCommand.simple("ls", "-la")
        result = execute_process(cmd)
        if result.is_success():
            print(result.stdout)
        
        # Runtime check with error handling
        cmd = ProcessCommand.for_runtime_check("podman")
        try:
            result = execute_process(cmd, raise_on_error=True)
            print("Podman available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Podman not found")
    """
    # Determine if we should check returncode
    check = raise_on_error if raise_on_error is not None else command.should_check_returncode()
    
    # Execute command
    result = subprocess.run(
        command.command,
        cwd=command.working_directory if command.has_working_directory() else None,
        timeout=command.timeout,
        capture_output=command.should_capture_output(),
        text=command.is_text_mode(),
        check=check,
    )
    
    # Convert to domain entity
    return ProcessResult.from_subprocess_result(result, command.command)

