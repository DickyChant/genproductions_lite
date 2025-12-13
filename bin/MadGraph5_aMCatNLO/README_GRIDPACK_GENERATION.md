# MadGraph5_aMCatNLO Gridpack Generation - Python Refactored Version

This directory contains a refactored, Python-based implementation of the gridpack generation system for MadGraph5_aMCatNLO. The new implementation provides better modularity, maintainability, and testability compared to the original bash script.

## Overview

The gridpack generation system has been reorganized into a modular Python library (`gridpack_lib/`) with the following components:

### Module Structure

```
gridpack_lib/
├── __init__.py              # Package initialization
├── config.py                # Configuration and argument parsing
├── card_validator.py        # Card validation utilities
├── environment.py           # CMSSW environment setup
├── madgraph_setup.py        # MadGraph download and configuration
├── process_generator.py     # Process generation and integration
├── tarball_creator.py       # Gridpack tarball creation
├── gridpack_generator.py    # Main orchestrator
└── utils.py                 # Common utility functions
```

### Main Entry Point

- `gridpack_generation.py` - Main executable script (Python-based)
- `gridpack_generation.sh` - Original bash script (kept for reference)

## Features

### Improvements Over Bash Version

1. **Modular Design**: Code is organized into logical modules, each with a single responsibility
2. **Type Hints**: Python type hints improve code readability and catch errors early
3. **Error Handling**: Better error messages and exception handling
4. **Testability**: Each module can be tested independently
5. **Documentation**: Comprehensive docstrings and comments
6. **Maintainability**: Easier to understand, modify, and extend

### Key Capabilities

- Automatic SCRAM architecture and CMSSW version detection
- Card validation with detailed error messages
- Support for both LO and NLO processes
- Reweighting and MadSpin support
- Multiple queue systems (local, condor, LSF)
- Incremental job steps (CODEGEN, INTEGRATE, etc.)

## Usage

### Basic Usage

```bash
# Generate gridpack with default settings (local execution)
./gridpack_generation.py <process_name> <cards_directory>

# Example
./gridpack_generation.py ttbar cards/ttbar
```

### Advanced Usage

```bash
# Full syntax
./gridpack_generation.py <name> <carddir> [queue] [jobstep] [scram_arch] [cmssw_version]

# Generate on condor queue
./gridpack_generation.py ttbar cards/ttbar condor

# Only run code generation step
./gridpack_generation.py ttbar cards/ttbar local CODEGEN

# Specify CMSSW version
./gridpack_generation.py ttbar cards/ttbar local ALL slc7_amd64_gcc10 CMSSW_12_4_8
```

### Command Line Arguments

| Argument | Description | Default | Options |
|----------|-------------|---------|---------|
| `name` | Process name (required) | - | Any string |
| `carddir` | Path to cards directory (required) | - | Relative path |
| `queue` | Queue system to use | `local` | `local`, `condor`, `condor_spool`, `pdmv`, or LSF queue name |
| `jobstep` | Job step to execute | `ALL` | `ALL`, `CODEGEN`, `INTEGRATE`, `MADSPIN` |
| `scram_arch` | SCRAM architecture | Auto-detect | e.g., `slc7_amd64_gcc10` |
| `cmssw_version` | CMSSW version | Auto-detect | e.g., `CMSSW_12_4_8` |

### Job Steps

- **ALL**: Complete gridpack generation (default)
- **CODEGEN**: Only generate process code
- **INTEGRATE**: Run integration (assumes CODEGEN already done)
- **MADSPIN**: MadSpin step (not yet split from INTEGRATE)

## Required Cards

Place the following cards in your cards directory:

### Mandatory Cards

- `<name>_proc_card.dat` - Process definition card
- `<name>_run_card.dat` - Run parameters card

### Optional Cards

- `<name>_param_card.dat` - Model parameters
- `<name>_customizecards.dat` - Parameter customizations
- `<name>_reweight_card.dat` - Reweighting configuration
- `<name>_madspin_card.dat` - MadSpin decay configuration
- `<name>_extramodels.dat` - Additional BSM models to load
- `<name>_cuts.f` - Custom cuts
- `<name>_FKS_params.dat` - FKS parameters (NLO)
- `<name>_setscales.f` - Custom scale setting
- `<name>_reweight_xsec.f` - Custom reweighting
- `<name>_externaltarball.dat` - External tarball configuration
- `<name>_patch_me.sh` - Matrix element patches
- `<name>*.patch` - Custom patches for MadGraph

## Card Directory Structure

```
cards/
└── myprocess/
    ├── myprocess_proc_card.dat
    ├── myprocess_run_card.dat
    ├── myprocess_param_card.dat       (optional)
    ├── myprocess_customizecards.dat   (optional)
    ├── myprocess_reweight_card.dat    (optional)
    └── myprocess_madspin_card.dat     (optional)
```

## Output

The script generates a tarball in the production home directory:

```
<name>_<scram_arch>_<cmssw_version>_tarball.tar.xz
```

For example: `ttbar_slc7_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz`

## Examples

### Example 1: Local LO Process

```bash
# Create cards directory
mkdir -p cards/zjet

# Add proc_card.dat and run_card.dat
# ... (prepare your cards)

# Generate gridpack
./gridpack_generation.py zjet cards/zjet local
```

### Example 2: NLO Process with Reweighting on Condor

```bash
# Prepare cards with reweight card
mkdir -p cards/ttbar_nlo
# ... add cards including ttbar_nlo_reweight_card.dat

# Generate on condor
./gridpack_generation.py ttbar_nlo cards/ttbar_nlo condor
```

### Example 3: Two-Step Generation

```bash
# Step 1: Generate code only
./gridpack_generation.py higgs cards/higgs local CODEGEN

# Step 2: Run integration later
./gridpack_generation.py higgs cards/higgs local INTEGRATE
```

## Environment Requirements

- Python 3.6 or later
- CVMFS access to `/cvmfs/cms.cern.ch`
- Appropriate CMSSW release
- Internet access for downloading MadGraph (if not cached)

## Supported Systems

The script auto-detects the operating system and sets appropriate defaults:

- **RedHat/CentOS 7**: `slc7_amd64_gcc10`, `CMSSW_12_4_8`
- **RedHat/CentOS 8**: `el8_amd64_gcc10`, `CMSSW_12_4_8`
- **RedHat/CentOS 9**: `el9_amd64_gcc11`, `CMSSW_13_2_9`

## Troubleshooting

### Common Issues

1. **"Card validation failed"**
   - Check that all required cards exist
   - Verify card naming matches process name
   - Review error messages for specific issues

2. **"Environment setup failed"**
   - Ensure CVMFS is accessible
   - Check that you're not already in a CMSSW environment
   - Verify scram_arch is compatible with your OS

3. **"Process generation failed"**
   - Check MadGraph log files
   - Verify proc_card syntax
   - Ensure required models are available

4. **"This script must be run in a clean environment"**
   - Exit any existing CMSSW environment
   - Start from a fresh shell

### Debugging

Enable verbose output by checking log files:

- `<name>.log` - Main log file in working directory
- `gridpack_generation*.log` - Detailed generation logs

## Migration from Bash Script

The Python version is designed to be a drop-in replacement for the bash script:

### Backward Compatibility

The command line interface is identical:
```bash
# Old (bash)
./gridpack_generation.sh ttbar cards/ttbar local

# New (Python)
./gridpack_generation.py ttbar cards/ttbar local
```

### Bash Script Wrapper

If you need to keep using the bash script interface, you can create a wrapper:

```bash
#!/bin/bash
# gridpack_generation_wrapper.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "${SCRIPT_DIR}/gridpack_generation.py" "$@"
```

## Architecture Details

### Design Principles

1. **Separation of Concerns**: Each module handles a specific aspect
2. **Single Responsibility**: Each class has one primary job
3. **Dependency Injection**: Components receive dependencies as parameters
4. **Configuration Object**: Centralized configuration management
5. **Error Handling**: Graceful error handling with informative messages

### Module Responsibilities

- **config.py**: Parse CLI args, manage configuration, validate environment
- **card_validator.py**: Validate all input cards for correctness
- **environment.py**: Set up CMSSW environment, SCRAM, LHAPDF
- **madgraph_setup.py**: Download MadGraph, apply patches, configure
- **process_generator.py**: Generate process code, prepare for integration
- **tarball_creator.py**: Create final compressed gridpack tarball
- **gridpack_generator.py**: Orchestrate all steps, main workflow
- **utils.py**: Shared utility functions

### Data Flow

```
CLI Arguments → Config → GridpackGenerator
                  ↓
         ┌────────┴────────┐
         ↓                 ↓
    CardValidator    EnvironmentManager
         ↓                 ↓
    Validation       CMSSW Setup
         ↓                 ↓
         └────────┬────────┘
                  ↓
          MadGraphSetup
                  ↓
          ProcessGenerator
                  ↓
          TarballCreator
                  ↓
          Final Gridpack
```

## Contributing

When modifying the code:

1. Follow Python PEP 8 style guidelines
2. Add docstrings to all functions and classes
3. Include type hints for function parameters and returns
4. Update this README if adding new features
5. Test changes with both LO and NLO processes

## References

- [MadGraph5_aMC@NLO Documentation](https://launchpad.net/mg5amcnlo)
- [CMS Twiki Guide](https://twiki.cern.ch/twiki/bin/view/CMS/QuickGuideMadGraph5aMCatNLO)
- [Original genproductions repository](https://github.com/cms-sw/genproductions)

## License

This code is part of the CMS genproductions repository and follows the same license terms.

## Version History

- **v1.0.0** (2024): Initial Python refactoring
  - Modular architecture
  - Improved error handling
  - Comprehensive documentation
  - Backward compatible with bash script
