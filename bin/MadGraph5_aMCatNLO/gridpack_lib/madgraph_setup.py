"""MadGraph setup and configuration utilities."""

import os
import subprocess
import shutil
from typing import List, Optional


class MadGraphSetup:
    """Manages MadGraph download, setup, and configuration."""
    
    # MadGraph version and source
    MG_VERSION = "2.9.13"
    MG_EXT = ".tar.gz"
    
    def __init__(self, config, env_manager):
        """Initialize MadGraph setup manager."""
        self.config = config
        self.env_manager = env_manager
        self.mg_filename = f"MG5_aMC_v{self.MG_VERSION}{self.MG_EXT}"
        self.mg_source = f"https://cms-project-generators.web.cern.ch/cms-project-generators/{self.mg_filename}"
        self.mg_basedir_orig = f"MG5_aMC_v{self.MG_VERSION}".replace('.', '_')
    
    def download_and_setup(self) -> bool:
        """Download and set up MadGraph.
        
        Returns:
            True if successful, False otherwise
        """
        print("Setting up MadGraph...")
        
        # Download MadGraph
        if not self._download_madgraph():
            return False
        
        # Extract MadGraph
        if not self._extract_madgraph():
            return False
        
        # Apply patches
        if not self._apply_patches():
            return False
        
        # Copy plugins
        self._copy_plugins()
        
        # Copy bias module if present
        self._copy_bias_module()
        
        # Configure MadGraph
        if not self._configure_madgraph():
            return False
        
        # Load extra models if needed
        self._load_extra_models()
        
        print("MadGraph setup complete")
        return True
    
    def _download_madgraph(self) -> bool:
        """Download MadGraph tarball.
        
        Returns:
            True if successful, False otherwise
        """
        if os.path.exists(self.mg_basedir_orig):
            print(f"MadGraph directory {self.mg_basedir_orig} already exists, skipping download")
            return True
        
        if os.path.exists(self.mg_filename):
            print(f"MadGraph tarball {self.mg_filename} already exists, skipping download")
            return True
        
        print(f"Downloading MadGraph from {self.mg_source}")
        
        try:
            result = subprocess.run(
                ['wget', '--no-check-certificate', self.mg_source],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error downloading MadGraph: {e}")
            return False
    
    def _extract_madgraph(self) -> bool:
        """Extract MadGraph tarball.
        
        Returns:
            True if successful, False otherwise
        """
        if os.path.exists(self.mg_basedir_orig):
            print(f"MadGraph already extracted to {self.mg_basedir_orig}")
            return True
        
        print(f"Extracting {self.mg_filename}")
        
        try:
            subprocess.run(
                ['tar', 'xzf', self.mg_filename],
                check=True
            )
            
            # Remove tarball to save space
            os.remove(self.mg_filename)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error extracting MadGraph: {e}")
            return False
    
    def _apply_patches(self) -> bool:
        """Apply patches to MadGraph.
        
        Returns:
            True if successful, False otherwise
        """
        patches_dir = os.path.join(self.config.prodhome, 'patches')
        
        if not os.path.exists(patches_dir):
            print("No patches directory found, skipping patches")
            return True
        
        patch_files = sorted([f for f in os.listdir(patches_dir) if f.endswith('.patch')])
        
        if not patch_files:
            print("No patches found, skipping")
            return True
        
        print("Applying patches to MadGraph")
        os.chdir(self.mg_basedir_orig)
        
        for patch_file in patch_files:
            patch_path = os.path.join(patches_dir, patch_file)
            print(f"  Applying {patch_file}")
            
            try:
                with open(patch_path, 'r') as f:
                    subprocess.run(
                        ['patch', '-p1'],
                        stdin=f,
                        check=True
                    )
            except subprocess.CalledProcessError as e:
                print(f"Error applying patch {patch_file}: {e}")
                return False
        
        # Apply custom user patches if present
        if os.path.exists(self.config.cardsdir):
            user_patches = sorted([
                f for f in os.listdir(self.config.cardsdir)
                if f.startswith(self.config.name) and f.endswith('.patch')
            ])
        else:
            user_patches = []
        
        for patch_file in user_patches:
            patch_path = os.path.join(self.config.cardsdir, patch_file)
            print(f"  WARNING: Applying custom user patch {patch_file}")
            print("  I hope you know what you're doing!")
            
            try:
                with open(patch_path, 'r') as f:
                    subprocess.run(
                        ['patch', '-p1'],
                        stdin=f,
                        check=True
                    )
            except subprocess.CalledProcessError as e:
                print(f"Error applying user patch {patch_file}: {e}")
                return False
        
        os.chdir('..')
        return True
    
    def _copy_plugins(self):
        """Copy required plugins to MadGraph."""
        plugin_src = os.path.join(self.config.prodhome, 'PLUGIN', 'CMS_CLUSTER')
        plugin_dst = os.path.join(self.mg_basedir_orig, 'PLUGIN', 'CMS_CLUSTER')
        
        if os.path.exists(plugin_src):
            print("Copying CMS_CLUSTER plugin")
            os.makedirs(os.path.dirname(plugin_dst), exist_ok=True)
            shutil.copytree(plugin_src, plugin_dst, dirs_exist_ok=True)
    
    def _copy_bias_module(self):
        """Copy bias module if present."""
        bias_src = os.path.join(self.config.cardsdir, 'BIAS')
        
        if not os.path.exists(bias_src):
            return
        
        print("Copying bias module")
        bias_dst = os.path.join(
            self.mg_basedir_orig, 'Template', 'LO', 'Source', 'BIAS'
        )
        
        for item in os.listdir(bias_src):
            src_path = os.path.join(bias_src, item)
            dst_path = os.path.join(bias_dst, item)
            
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)
    
    def _configure_madgraph(self) -> bool:
        """Configure MadGraph settings.
        
        Returns:
            True if successful, False otherwise
        """
        print("Configuring MadGraph")
        
        lhapdf_config = self.env_manager.get_lhapdf_config()
        
        config_lines = [
            "set auto_update 0",
            "set automatic_html_opening False",
            "set auto_convert_model True",
        ]
        
        if self.config.is_cms_connect > 0:
            config_lines.append("set output_dependencies internal")
        
        config_lines.append(f"set lhapdf_py3 {lhapdf_config}")
        
        # Set run mode based on queue
        if self.config.queue == "local":
            config_lines.append("set run_mode 2")
        elif self.config.queue == "pdmv":
            config_lines.append("set run_mode 2")
            if self.config.nb_core:
                config_lines.append(f"set nb_core {self.config.nb_core}")
        else:
            # Suppress LSF emails
            os.environ['LSB_JOB_REPORT_MAIL'] = "N"
            
            config_lines.append("set run_mode 1")
            
            if self.config.queue == "condor":
                config_lines.extend([
                    "set cluster_type cms_condor",
                    "set cluster_queue None"
                ])
            elif self.config.queue == "condor_spool":
                config_lines.extend([
                    "set cluster_type cms_condor_spool",
                    "set cluster_queue None"
                ])
            else:
                config_lines.append("set cluster_type cms_lsf")
            
            # Set retry parameters
            if self.config.is_cms_connect > 0:
                n_retries = 10
                long_wait = 300
                short_wait = 120
            else:
                n_retries = 3
                long_wait = 60
                short_wait = 30
            
            config_lines.extend([
                f"set cluster_status_update {long_wait} {short_wait}",
                f"set cluster_nb_retry {n_retries}",
                "set cluster_retry_wait 300"
            ])
        
        config_lines.append("save options --all")
        
        # Write and execute configuration script
        config_script = os.path.join(os.getcwd(), 'mgconfigscript')
        with open(config_script, 'w') as f:
            f.write('\n'.join(config_lines) + '\n')
        
        mg5_bin = os.path.join(self.mg_basedir_orig, 'bin', 'mg5_aMC')
        
        try:
            subprocess.run(
                [mg5_bin, config_script],
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error configuring MadGraph: {e}")
            return False
    
    def _load_extra_models(self):
        """Load extra BSM models if specified."""
        extramodels_file = os.path.join(
            self.config.cardsdir, f"{self.config.name}_extramodels.dat"
        )
        
        if not os.path.exists(extramodels_file):
            return
        
        print(f"Loading extra models from {extramodels_file}")
        
        with open(extramodels_file, 'r') as f:
            for line in f:
                # Strip comments
                line = line.split('#')[0].strip()
                
                if not line:
                    continue
                
                print(f"  Loading extra model {line}")
                
                # Download model
                model_url = f"https://cms-project-generators.web.cern.ch/cms-project-generators/{line}"
                
                try:
                    subprocess.run(
                        ['wget', '--no-check-certificate', model_url],
                        check=True
                    )
                    
                    # Extract model
                    models_dir = os.path.join(self.mg_basedir_orig, 'models')
                    os.chdir(models_dir)
                    
                    if line.endswith('.zip'):
                        subprocess.run(['unzip', f"../{line}"], check=True)
                    elif line.endswith('.tgz'):
                        subprocess.run(['tar', 'zxvf', f"../{line}"], check=True)
                    elif line.endswith('.tar'):
                        subprocess.run(['tar', 'xavf', f"../{line}"], check=True)
                    else:
                        print(f"Unknown archive format for {line}")
                    
                    os.chdir('..')
                    
                except subprocess.CalledProcessError as e:
                    print(f"Error loading extra model {line}: {e}")
