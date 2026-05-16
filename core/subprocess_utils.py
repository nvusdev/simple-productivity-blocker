import subprocess
import logging

def run_system_command(cmd_list, elevate=False, check=True, timeout=15):
    """
    Standardized wrapper for running system commands (schtasks, icacls, takeown, etc).
    - Ensures hidden window (CREATE_NO_WINDOW).
    - Standardizes output capture and error logging.
    """
    logger = logging.getLogger("SPB_System")
    
    # 0x08000000 = CREATE_NO_WINDOW
    creation_flags = 0x08000000
    
    try:
        # Standardize command to list of strings
        if isinstance(cmd_list, str):
            cmd_list = [cmd_list]
            
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout,
            creationflags=creation_flags
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(cmd_list)}")
        logger.error(f"Exit Code: {e.returncode}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr.strip()}")
        if check:
            raise
        return e
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {' '.join(cmd_list)}")
        if check:
            raise
        return None
    except Exception as e:
        logger.error(f"Subprocess error: {e}")
        if check:
            raise
        return None
