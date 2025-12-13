"""Configuration management for gridpack generation."""

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class GridpackConfig:
    """Configuration for gridpack generation."""
    
    name: str
    carddir: str
    queue: str = "local"
    jobstep: str = "ALL"
    scram_arch: Optional[str] = None
    cmssw_version: Optional[str] = None
    prodhome: Optional[str] = None
    is_cms_connect: int = 0
    nb_core: Optional[int] = None
    
    def __post_init__(self):
        """Validate and set defaults after initialization."""
        if self.prodhome is None:
            self.prodhome = os.getcwd()
            
        # Determine scram_arch and cmssw_version from system if not provided
        if self.scram_arch is None or self.cmssw_version is None:
            self._set_defaults_from_system()
    
    def _set_defaults_from_system(self):
        """Set default SCRAM arch and CMSSW version based on system."""
        try:
            with open('/etc/redhat-release', 'r') as f:
                system_release = f.read()
        except FileNotFoundError:
            print("Warning: Could not read /etc/redhat-release")
            system_release = ""
        
        if self.scram_arch is None:
            if 'release 7' in system_release:
                self.scram_arch = 'slc7_amd64_gcc10'
            elif 'release 8' in system_release:
                self.scram_arch = 'el8_amd64_gcc10'
            elif 'release 9' in system_release:
                self.scram_arch = 'el9_amd64_gcc11'
            else:
                # Default for non-RedHat systems or when file is not available
                self.scram_arch = 'slc7_amd64_gcc10'
                if not system_release:
                    print("Warning: Using default scram_arch (slc7_amd64_gcc10)")
        
        if self.cmssw_version is None:
            if 'release 7' in system_release:
                self.cmssw_version = 'CMSSW_12_4_8'
            elif 'release 8' in system_release:
                self.cmssw_version = 'CMSSW_12_4_8'
            elif 'release 9' in system_release:
                self.cmssw_version = 'CMSSW_13_2_9'
            else:
                # Default for non-RedHat systems or when file is not available
                self.cmssw_version = 'CMSSW_12_4_8'
                if not system_release:
                    print("Warning: Using default CMSSW version (CMSSW_12_4_8)")
    
    @property
    def cardsdir(self) -> str:
        """Get full path to cards directory."""
        return os.path.join(self.prodhome, self.carddir)
    
    @property
    def gen_folder(self) -> str:
        """Get generation folder path."""
        return os.path.join(os.getcwd(), self.name)
    
    @property
    def workdir(self) -> str:
        """Get work directory path."""
        return os.path.join(self.gen_folder, f"{self.name}_gridpack", "work")
    
    @property
    def logfile(self) -> str:
        """Get log file path."""
        return os.path.join(os.getcwd(), f"{self.name}.log")


def parse_arguments() -> GridpackConfig:
    """Parse command line arguments and return configuration."""
    parser = argparse.ArgumentParser(
        description='Generate MadGraph5_aMCatNLO gridpack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s myprocess cards/myprocess local
  %(prog)s myprocess cards/myprocess condor ALL slc7_amd64_gcc10 CMSSW_12_4_8
  
Job steps: ALL, CODEGEN, INTEGRATE, MADSPIN
Queues: local, condor, condor_spool, pdmv, or any LSF queue name
        """
    )
    
    parser.add_argument('name', help='Name of the production (process name)')
    parser.add_argument('carddir', help='Relative path to cards directory')
    parser.add_argument('queue', nargs='?', default='local',
                        help='Queue selection (default: local)')
    parser.add_argument('jobstep', nargs='?', default='ALL',
                        choices=['ALL', 'CODEGEN', 'INTEGRATE', 'MADSPIN'],
                        help='Job step to execute (default: ALL)')
    parser.add_argument('scram_arch', nargs='?',
                        help='SCRAM architecture (default: auto-detect)')
    parser.add_argument('cmssw_version', nargs='?',
                        help='CMSSW version (default: auto-detect)')
    parser.add_argument('--nb-core', type=int,
                        help='Number of cores for pdmv queue')
    parser.add_argument('--is-cms-connect', action='store_true',
                        help='Running on CMS Connect')
    
    args = parser.parse_args()
    
    return GridpackConfig(
        name=args.name,
        carddir=args.carddir,
        queue=args.queue,
        jobstep=args.jobstep,
        scram_arch=args.scram_arch,
        cmssw_version=args.cmssw_version,
        is_cms_connect=1 if args.is_cms_connect else 0,
        nb_core=args.nb_core
    )


def validate_environment(config: GridpackConfig) -> None:
    """Validate that environment is clean for gridpack generation."""
    if os.environ.get('CMSSW_BASE'):
        print(f"Error: This script must be run in a clean environment.")
        print(f"You already have a CMSSW environment set up for {os.environ.get('CMSSW_VERSION')}.")
        print("Please try again from a clean shell.")
        sys.exit(1)
