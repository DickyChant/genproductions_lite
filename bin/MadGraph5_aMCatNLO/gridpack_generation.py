#!/usr/bin/env python3
"""
MadGraph5_aMCatNLO Gridpack Generation Script

This script generates gridpacks for MadGraph5_aMCatNLO in a modular, Python-based approach.
It replaces the traditional bash-based gridpack_generation.sh script with a more maintainable
and testable Python implementation.

Usage:
    gridpack_generation.py <name> <carddir> [queue] [jobstep] [scram_arch] [cmssw_version]

Arguments:
    name         : Name of the production (process name)
    carddir      : Relative path to cards directory
    queue        : Queue selection (default: local)
                   Options: local, condor, condor_spool, pdmv, or any LSF queue name
    jobstep      : Job step to execute (default: ALL)
                   Options: ALL, CODEGEN, INTEGRATE, MADSPIN
    scram_arch   : SCRAM architecture (default: auto-detect from OS)
    cmssw_version: CMSSW version (default: auto-detect from OS)

Examples:
    # Generate gridpack locally
    ./gridpack_generation.py myprocess cards/myprocess

    # Generate on condor queue with specific CMSSW
    ./gridpack_generation.py myprocess cards/myprocess condor ALL slc7_amd64_gcc10 CMSSW_12_4_8

    # Only run code generation step
    ./gridpack_generation.py myprocess cards/myprocess local CODEGEN

Card Files Required:
    <name>_proc_card.dat  : Process card (mandatory)
    <name>_run_card.dat   : Run card (mandatory)
    <name>_param_card.dat : Parameter card (optional)
    <name>_customizecards.dat : Customization card (optional)
    <name>_reweight_card.dat : Reweighting card (optional)
    <name>_madspin_card.dat : MadSpin card (optional)

For more information, see the README.md file.
"""

import sys
import os

# Add gridpack_lib to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gridpack_lib.config import parse_arguments, validate_environment
from gridpack_lib.gridpack_generator import GridpackGenerator


def main():
    """Main entry point for gridpack generation."""
    # Parse command line arguments
    try:
        config = parse_arguments()
    except SystemExit:
        # argparse will handle help and errors
        return 1
    
    # Validate environment
    validate_environment(config)
    
    # Create and run generator
    generator = GridpackGenerator(config)
    return generator.run()


if __name__ == '__main__':
    sys.exit(main())
