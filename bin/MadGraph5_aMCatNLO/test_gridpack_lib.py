#!/usr/bin/env python3
"""
Basic tests for the gridpack generation modules.

These tests validate the core functionality without requiring a full CMSSW environment.
"""

import unittest
import sys
import os
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gridpack_lib.config import GridpackConfig
from gridpack_lib.card_validator import CardValidator


class TestGridpackConfig(unittest.TestCase):
    """Test GridpackConfig class."""
    
    def test_basic_config(self):
        """Test basic configuration creation."""
        config = GridpackConfig(
            name="test_process",
            carddir="cards/test",
            queue="local",
            jobstep="ALL"
        )
        
        self.assertEqual(config.name, "test_process")
        self.assertEqual(config.carddir, "cards/test")
        self.assertEqual(config.queue, "local")
        self.assertEqual(config.jobstep, "ALL")
    
    def test_config_defaults(self):
        """Test that defaults are set appropriately."""
        config = GridpackConfig(
            name="test",
            carddir="cards/test"
        )
        
        # Should have defaults
        self.assertEqual(config.queue, "local")
        self.assertEqual(config.jobstep, "ALL")
        self.assertIsNotNone(config.scram_arch)
        self.assertIsNotNone(config.cmssw_version)
    
    def test_config_properties(self):
        """Test configuration properties."""
        config = GridpackConfig(
            name="test",
            carddir="cards/test",
            prodhome="/test/home"
        )
        
        self.assertEqual(config.cardsdir, "/test/home/cards/test")
        self.assertIn("test", config.gen_folder)
        self.assertIn("test_gridpack", config.workdir)


class TestCardValidator(unittest.TestCase):
    """Test CardValidator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.cards_dir = os.path.join(self.test_dir, "cards", "test_process")
        os.makedirs(self.cards_dir)
        
        # Create config
        self.config = GridpackConfig(
            name="test_process",
            carddir="cards/test_process",
            prodhome=self.test_dir
        )
        
        self.validator = CardValidator(self.config)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_missing_cards_dir(self):
        """Test validation with missing cards directory."""
        config = GridpackConfig(
            name="test",
            carddir="nonexistent",
            prodhome=self.test_dir
        )
        validator = CardValidator(config)
        
        self.assertFalse(validator.validate_all())
    
    def test_missing_required_cards(self):
        """Test validation with missing required cards."""
        # Cards directory exists but no cards
        self.assertFalse(self.validator.validate_all())
    
    def test_valid_cards(self):
        """Test validation with valid cards."""
        # Create required cards
        proc_card = os.path.join(self.cards_dir, "test_process_proc_card.dat")
        run_card = os.path.join(self.cards_dir, "test_process_run_card.dat")
        
        with open(proc_card, 'w') as f:
            f.write("# Process card\n")
        
        with open(run_card, 'w') as f:
            f.write("# Run card\n")
        
        self.assertTrue(self.validator.validate_all())
    
    def test_customizecards_compute_widths(self):
        """Test detection of problematic compute_widths."""
        # Create required cards first
        proc_card = os.path.join(self.cards_dir, "test_process_proc_card.dat")
        run_card = os.path.join(self.cards_dir, "test_process_run_card.dat")
        
        with open(proc_card, 'w') as f:
            f.write("# Process card\n")
        
        with open(run_card, 'w') as f:
            f.write("# Run card\n")
        
        # Create customizecards with compute_widths
        custom_card = os.path.join(self.cards_dir, "test_process_customizecards.dat")
        with open(custom_card, 'w') as f:
            f.write("compute_widths X\n")
        
        self.assertFalse(self.validator.validate_all())
    
    def test_madspin_typo(self):
        """Test detection of madspin typo."""
        # Create required cards first
        proc_card = os.path.join(self.cards_dir, "test_process_proc_card.dat")
        run_card = os.path.join(self.cards_dir, "test_process_run_card.dat")
        
        with open(proc_card, 'w') as f:
            f.write("# Process card\n")
        
        with open(run_card, 'w') as f:
            f.write("# Run card\n")
        
        # Create madspin card with typo (intentional: 'weigth' instead of 'weight')
        # This tests the validator's ability to catch the known MG typo
        madspin_card = os.path.join(self.cards_dir, "test_process_madspin_card.dat")
        with open(madspin_card, 'w') as f:
            f.write("Nevents_for_max_weigth 100\n")  # Intentional typo
        
        self.assertFalse(self.validator.validate_all())


class TestHelp(unittest.TestCase):
    """Test help and command line interface."""
    
    def test_import_modules(self):
        """Test that all modules can be imported."""
        try:
            from gridpack_lib import config
            from gridpack_lib import card_validator
            from gridpack_lib import environment
            from gridpack_lib import madgraph_setup
            from gridpack_lib import process_generator
            from gridpack_lib import tarball_creator
            from gridpack_lib import gridpack_generator
            from gridpack_lib import utils
        except ImportError as e:
            self.fail(f"Failed to import module: {e}")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
