# IMPORTANT

This is not the full version genproductions setup, only a lite version removing unnecessary files to facilitate the CMS DAS in 2024 https://sihyunjeon.github.io/generators-cmsdaslpc2024/index.html.

For up-to-date and CMS official usages, please use https://github.com/cms-sw/genproductions.

## Recent Updates

### Python-based Gridpack Generation (MadGraph5_aMCatNLO)

The `gridpack_generation.sh` script in the MadGraph5_aMCatNLO folder has been refactored into a modular Python-based implementation (`gridpack_generation.py`). This provides:

- **Modular architecture**: Clean separation of concerns with dedicated modules for configuration, validation, environment setup, etc.
- **Better error handling**: More informative error messages and graceful failure handling
- **Testability**: Unit tests for core functionality
- **Maintainability**: Easier to understand, modify, and extend
- **Documentation**: Comprehensive README and inline documentation

See [bin/MadGraph5_aMCatNLO/README_GRIDPACK_GENERATION.md](bin/MadGraph5_aMCatNLO/README_GRIDPACK_GENERATION.md) for detailed documentation on the new Python-based system.

The original bash script is still available for reference, and the Python version is designed to be a drop-in replacement with the same command-line interface.
