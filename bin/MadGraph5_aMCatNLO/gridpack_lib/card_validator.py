"""Card validation utilities for gridpack generation."""

import os
import re
import sys
from typing import List


class CardValidator:
    """Validates MadGraph cards for gridpack generation."""
    
    def __init__(self, config):
        """Initialize card validator with configuration."""
        self.config = config
        self.cardsdir = config.cardsdir
        self.name = config.name
    
    def validate_all(self) -> bool:
        """Validate all required cards and return True if valid."""
        print("Validating cards...")
        
        # Check cards directory exists
        if not self._validate_cardsdir_exists():
            return False
        
        # Check required cards exist
        if not self._validate_required_cards():
            return False
        
        # Validate card contents
        if not self._validate_card_contents():
            return False
        
        print("Card validation successful")
        return True
    
    def _validate_cardsdir_exists(self) -> bool:
        """Check if cards directory exists."""
        if not os.path.isdir(self.cardsdir):
            print(f"{self.cardsdir} does not exist!")
            return False
        return True
    
    def _validate_required_cards(self) -> bool:
        """Check if required cards exist."""
        required_cards = [
            f"{self.name}_proc_card.dat",
            f"{self.name}_run_card.dat"
        ]
        
        for card in required_cards:
            card_path = os.path.join(self.cardsdir, card)
            if not os.path.isfile(card_path):
                print(f"{card_path} does not exist!")
                return False
        
        return True
    
    def _validate_card_contents(self) -> bool:
        """Validate contents of cards."""
        validators = [
            self._check_compute_widths,
            self._check_madspin_typo,
            self._check_weight_names
        ]
        
        for validator in validators:
            if not validator():
                return False
        
        return True
    
    def _check_compute_widths(self) -> bool:
        """Check for problematic compute_widths in customizecards."""
        customizecards_path = os.path.join(
            self.cardsdir, f"{self.name}_customizecards.dat"
        )
        
        if not os.path.exists(customizecards_path):
            return True
        
        with open(customizecards_path, 'r') as f:
            if 'compute_widths' in f.read():
                print("<<compute_widths X>> is used in your customizecards.dat")
                print("This could be problematic from time to time, so instead use")
                print("<<set decay wX AUTO>> for width computations.")
                print("Please take a look at 'compute_widths' under")
                print("'Troubleshooting_and_Suggestions' section:")
                print("https://twiki.cern.ch/twiki/bin/view/CMS/QuickGuideMadGraph5aMCatNLO")
                return False
        
        return True
    
    def _check_madspin_typo(self) -> bool:
        """Check for typo in madspin card."""
        madspin_card_path = os.path.join(
            self.cardsdir, f"{self.name}_madspin_card.dat"
        )
        
        if not os.path.exists(madspin_card_path):
            return True
        
        with open(madspin_card_path, 'r') as f:
            if 'Nevents_for_max_weigth' in f.read():
                print("Nevents_for_max_weigth typo is fixed to Nevents_for_max_weight")
                print(f"in MGv2.7.x releases. {madspin_card_path} contains")
                print("Nevents_for_max_weigth instead of Nevents_for_max_weight.")
                print("Please correct the typo.")
                return False
        
        return True
    
    def _check_weight_names(self) -> bool:
        """Check for problematic characters in weight names."""
        reweight_card_path = os.path.join(
            self.cardsdir, f"{self.name}_reweight_card.dat"
        )
        
        if not os.path.exists(reweight_card_path):
            return True
        
        problematic_chars = r"[!@#\$%^\&*()\+\[\]{}]"
        
        with open(reweight_card_path, 'r') as f:
            for line in f:
                if 'rwgt_name' in line:
                    # Extract weight name
                    if 'rwgt_name=' in line:
                        weight_name = line.split('rwgt_name=')[1].split()[0]
                        if re.search(problematic_chars, weight_name):
                            print(f"Please remove problematic characters from weight name: {weight_name}")
                            return False
        
        return True
    
    def check_5flavor_scheme(self, logfile: str) -> int:
        """Check if 5-flavor scheme is being used.
        
        Returns:
            1 if 5-flavor scheme, 0 otherwise, -1 if cannot determine
        """
        if not os.path.exists(logfile):
            return -1
        
        with open(logfile, 'r') as f:
            # Read last 999 lines
            lines = f.readlines()
            tail_lines = lines[-999:] if len(lines) > 999 else lines
            content = ''.join(tail_lines)
            
            # Check for b~...b or b...b~ patterns
            if re.search(r'^p *=.*b~.*b', content, re.MULTILINE) or \
               re.search(r'^p *=.*b.*b~', content, re.MULTILINE):
                return 1
        
        return 0
