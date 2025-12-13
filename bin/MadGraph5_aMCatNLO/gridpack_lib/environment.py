"""Environment setup utilities for gridpack generation."""

import os
import subprocess
import sys
from pathlib import Path


class EnvironmentManager:
    """Manages CMSSW environment setup and configuration."""
    
    def __init__(self, config):
        """Initialize environment manager with configuration."""
        self.config = config
    
    def setup_environment(self) -> bool:
        """Set up CMSSW environment for gridpack generation.
        
        Returns:
            True if setup successful, False otherwise
        """
        print("Setting up environment...")
        
        # Create generation folder if needed
        if not os.path.exists(self.config.gen_folder):
            os.makedirs(self.config.gen_folder, exist_ok=True)
        
        os.chdir(self.config.gen_folder)
        
        # Set up environment variables
        os.environ['SCRAM_ARCH'] = self.config.scram_arch
        os.environ['RELEASE'] = self.config.cmssw_version
        os.environ['VO_CMS_SW_DIR'] = '/cvmfs/cms.cern.ch'
        
        # Source CMSSW setup
        self._source_cmssw()
        
        # Create CMSSW project
        if not self._create_cmssw_project():
            return False
        
        # Change to work directory
        workdir = os.path.join(
            self.config.gen_folder, f"{self.config.name}_gridpack", "work"
        )
        os.makedirs(workdir, exist_ok=True)
        os.chdir(workdir)
        
        # Set up SCRAM runtime
        if not self._setup_scram_runtime():
            return False
        
        # Set up condor if needed
        if 'condor' in self.config.queue:
            self._setup_condor()
        
        print("Environment setup complete")
        return True
    
    def _source_cmssw(self):
        """Source CMSSW setup script."""
        # This sets up the environment variables
        # In bash script: source $VO_CMS_SW_DIR/cmsset_default.sh
        # In Python, we need to execute this and capture env vars
        cmd = f"source {os.environ['VO_CMS_SW_DIR']}/cmsset_default.sh && env"
        try:
            proc = subprocess.Popen(
                ['bash', '-c', cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = proc.communicate()
            
            # Parse environment variables
            for line in stdout.decode().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        except Exception as e:
            print(f"Warning: Could not source cmsset_default.sh: {e}")
    
    def _create_cmssw_project(self) -> bool:
        """Create CMSSW project area.
        
        Returns:
            True if successful, False otherwise
        """
        project_name = f"{self.config.name}_gridpack"
        
        if os.path.exists(project_name):
            print(f"Project {project_name} already exists, skipping creation")
            return True
        
        cmd = [
            'scram', 'project', '-n', project_name,
            'CMSSW', self.config.cmssw_version
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if not os.path.exists(project_name):
                print(f"Failed to create CMSSW project {project_name}")
                return False
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating CMSSW project: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return False
    
    def _setup_scram_runtime(self) -> bool:
        """Set up SCRAM runtime environment.
        
        Returns:
            True if successful, False otherwise
        """
        cmd = "eval `scram runtime -sh` && env"
        try:
            proc = subprocess.Popen(
                ['bash', '-c', cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = proc.communicate()
            
            # Parse and set environment variables
            for line in stdout.decode().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
            
            return True
        except Exception as e:
            print(f"Error setting up SCRAM runtime: {e}")
            return False
    
    def _setup_condor(self):
        """Set up HTCondor environment."""
        print("Setting up HTCondor for gridpack generation")
        source_script = os.path.join(
            self.config.prodhome, "Utilities", "source_condor.sh"
        )
        
        if os.path.exists(source_script):
            cmd = f"source {source_script} && env"
            try:
                proc = subprocess.Popen(
                    ['bash', '-c', cmd],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, _ = proc.communicate()
                
                for line in stdout.decode().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            except Exception as e:
                print(f"Warning: Could not source condor setup: {e}")
    
    def get_lhapdf_config(self) -> str:
        """Get LHAPDF config path.
        
        Returns:
            Path to lhapdf-config
        """
        lhapdf_data_path = os.environ.get('LHAPDF_DATA_PATH', '')
        if lhapdf_data_path:
            return os.path.join(lhapdf_data_path, '..', '..', 'bin', 'lhapdf-config')
        
        # Check for lhapdf6
        scram_arch = os.environ.get('SCRAM_ARCH', '')
        cmssw_base = os.environ.get('CMSSW_BASE', '')
        lhapdf6_tool = os.path.join(
            cmssw_base, 'config', 'toolbox', scram_arch,
            'tools', 'available', 'lhapdf6.xml'
        )
        
        if os.path.exists(lhapdf6_tool):
            # Parse XML to get LHAPDF6_BASE
            with open(lhapdf6_tool, 'r') as f:
                for line in f:
                    if 'LHAPDF6_BASE' in line and 'environment' in line:
                        # Extract path from XML
                        import re
                        match = re.search(r'default="([^"]+)"', line)
                        if match:
                            base_path = match.group(1)
                            return os.path.join(base_path, 'bin', 'lhapdf-config')
        
        return os.path.join(lhapdf_data_path, '..', '..', 'bin', 'lhapdf-config')
