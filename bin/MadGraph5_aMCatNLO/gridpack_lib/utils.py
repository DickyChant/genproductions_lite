"""Utility functions for gridpack generation."""

import os
import subprocess
import sys
from typing import Optional


def print_system_info():
    """Print system information."""
    import platform
    import datetime
    
    print(f"Starting job on {datetime.datetime.now()}")
    print(f"Running on {platform.uname().node}")
    
    try:
        with open('/etc/redhat-release', 'r') as f:
            print(f"System release: {f.read().strip()}")
    except FileNotFoundError:
        print("System release: Unknown (not RedHat-based)")


def check_git_status(prodhome: str, is_cms_connect: bool = False):
    """Check and print git status if git is available.
    
    Args:
        prodhome: Path to production home directory
        is_cms_connect: Whether running on CMS Connect
    """
    if is_cms_connect:
        # CMS Connect runs git status in its own script
        return
    
    if not shutil.which('git'):
        return
    
    original_dir = os.getcwd()
    
    try:
        os.chdir(prodhome)
        
        # Run git status
        subprocess.run(['git', '--no-pager', 'status'])
        
        print("Current git revision is:")
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True
        )
        print(result.stdout.strip())
        
        # Show diff
        subprocess.run(['git', '--no-pager', 'diff'])
        
    except Exception as e:
        print(f"Warning: Could not check git status: {e}")
    finally:
        os.chdir(original_dir)


def run_command(cmd: list, check: bool = True, env: Optional[dict] = None) -> bool:
    """Run a command and return success status.
    
    Args:
        cmd: Command and arguments as list
        check: Whether to raise exception on failure
        env: Optional environment variables
        
    Returns:
        True if successful, False otherwise
    """
    try:
        subprocess.run(cmd, check=check, env=env)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(cmd)}")
        print(f"Error: {e}")
        return False


def check_lxplus_eos():
    """Check if running on lxplus with problematic /eos/home path."""
    import platform
    
    if 'lxplus' not in platform.uname().node:
        return
    
    cwd = os.getcwd()
    if cwd.startswith('/eos/home-'):
        print("WARNING: Running in /eos/home-X/ which is not really stable.")
        print("Use /eos/user/X/ instead.")
        sys.exit(1)


import shutil
