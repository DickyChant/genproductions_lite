"""Tarball creation utilities."""

import os
import subprocess
import shutil
from pathlib import Path


class TarballCreator:
    """Creates gridpack tarball."""
    
    def __init__(self, config):
        """Initialize tarball creator."""
        self.config = config
    
    def create_tarball(self) -> bool:
        """Create gridpack tarball.
        
        Returns:
            True if successful, False otherwise
        """
        print("Creating tarball...")
        
        gridpack_dir = os.path.join(self.config.workdir, 'gridpack')
        
        if not os.path.exists(gridpack_dir):
            print(f"Gridpack directory {gridpack_dir} not found")
            return False
        
        os.chdir(gridpack_dir)
        
        # Determine XZ compression options
        if self.config.is_cms_connect > 0:
            xz_opt = "--lzma2=preset=2,dict=256MiB"
        else:
            xz_opt = "--lzma2=preset=9,dict=512MiB"
        
        # Create InputCards directory
        input_cards_dir = 'InputCards'
        os.makedirs(input_cards_dir, exist_ok=True)
        
        # Copy cards
        self._copy_input_cards(input_cards_dir)
        
        # Determine extra files to include
        extra_files = self._get_extra_files()
        
        # Create tarball
        tarball_name = f"{self.config.name}_{self.config.scram_arch}_{self.config.cmssw_version}_tarball.tar.xz"
        tarball_path = os.path.join(self.config.prodhome, tarball_name)
        
        # Files to include in tarball
        files_to_tar = [
            'mgbasedir',
            'process',
            'runcmsgrid.sh',
            'InputCards'
        ]
        
        # Add gridpack_generation logs
        log_files = [f for f in os.listdir('.') if f.startswith('gridpack_generation') and f.endswith('.log')]
        files_to_tar.extend(log_files)
        
        # Add extra files
        files_to_tar.extend(extra_files)
        
        # Create tarball
        env = os.environ.copy()
        env['XZ_OPT'] = xz_opt
        
        cmd = ['tar', '-cJpf', tarball_path] + files_to_tar
        
        try:
            subprocess.run(cmd, env=env, check=True)
            print(f"Gridpack created successfully at {tarball_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating tarball: {e}")
            return False
    
    def _copy_input_cards(self, input_cards_dir: str):
        """Copy input cards to InputCards directory.
        
        Args:
            input_cards_dir: Path to InputCards directory
        """
        # Copy all cards matching the process name
        for filename in os.listdir(self.config.cardsdir):
            if filename.startswith(self.config.name):
                src = os.path.join(self.config.cardsdir, filename)
                dst = os.path.join(input_cards_dir, filename)
                
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
        
        # Copy BIAS directory if present
        bias_src = os.path.join(self.config.cardsdir, 'BIAS')
        if os.path.exists(bias_src):
            bias_dst = os.path.join(input_cards_dir, 'BIAS')
            shutil.copytree(bias_src, bias_dst, dirs_exist_ok=True)
    
    def _get_extra_files(self) -> list:
        """Get list of extra files to include in tarball.
        
        Returns:
            List of extra filenames
        """
        extra_files = []
        
        # Check for external tarball
        external_tarball_card = os.path.join(
            self.config.cardsdir, f"{self.config.name}_externaltarball.dat"
        )
        
        if os.path.exists(external_tarball_card):
            extra_files.append('external_tarball')
            extra_files.append('header_for_madspin.txt')
        
        # Check for merge.pl script
        if os.path.exists('merge.pl'):
            extra_files.append('merge.pl')
        
        return extra_files
