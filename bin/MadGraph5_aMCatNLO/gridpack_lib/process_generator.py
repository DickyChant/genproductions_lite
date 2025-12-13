"""Process generation utilities."""

import os
import subprocess
import shutil
from pathlib import Path


class ProcessGenerator:
    """Manages MadGraph process generation and integration."""
    
    def __init__(self, config, mg_setup, env_manager):
        """Initialize process generator."""
        self.config = config
        self.mg_setup = mg_setup
        self.env_manager = env_manager
        self.is5flavor_scheme = -1
        self.is_nlo = False
    
    def generate_process(self) -> bool:
        """Generate process code.
        
        Returns:
            True if successful, False otherwise
        """
        print("Generating process code...")
        
        # Prepare process card
        proc_card_path = os.path.join(
            self.config.cardsdir, f"{self.config.name}_proc_card.dat"
        )
        local_proc_card = f"{self.config.name}_proc_card.dat"
        shutil.copy(proc_card_path, local_proc_card)
        
        # Add display multiparticles to proc card
        with open(local_proc_card, 'a') as f:
            f.write('\ndisplay multiparticles\n')
        
        # Set LHAPDF configuration workaround
        self._set_lhapdf_workaround()
        
        # Check if MadSTR plugin is needed
        run_madstr = self._check_madstr_needed()
        
        # Run MadGraph to generate process
        mg5_bin = os.path.join(self.mg_setup.mg_basedir_orig, 'bin', 'mg5_aMC')
        
        if run_madstr:
            print("Invoking MadSTR plugin when starting MG5_aMC@NLO")
            # Copy MadSTR plugin
            madstr_src = os.path.join(self.config.prodhome, 'PLUGIN', 'MadSTR')
            madstr_dst = os.path.join(self.mg_setup.mg_basedir_orig, 'PLUGIN', 'MadSTR')
            if os.path.exists(madstr_src):
                shutil.copytree(madstr_src, madstr_dst, dirs_exist_ok=True)
            
            cmd = [mg5_bin, '--mode=MadSTR', local_proc_card]
        else:
            cmd = [mg5_bin, local_proc_card]
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error generating process: {e}")
            return False
        
        # Check for 5-flavor scheme
        self.is5flavor_scheme = self._check_5flavor_scheme()
        
        # Set LHAPDF configuration again after code generation
        self._set_lhapdf_workaround()
        
        # Apply matrix element patches if present
        self._apply_me_patches()
        
        print("Process generation complete")
        return True
    
    def _set_lhapdf_workaround(self):
        """Set LHAPDF configuration workaround."""
        lhapdf_config = self.env_manager.get_lhapdf_config()
        
        # Get LHAPDF data directory
        try:
            result = subprocess.run(
                [lhapdf_config, '--datadir'],
                capture_output=True,
                text=True,
                check=True
            )
            lhapdf_datadir = result.stdout.strip()
        except:
            lhapdf_datadir = os.environ.get('LHAPDF_DATA_PATH', '')
        
        config_file = os.path.join(
            self.mg_setup.mg_basedir_orig,
            'input', 'mg5_configuration.txt'
        )
        
        with open(config_file, 'a') as f:
            f.write(f"cluster_local_path = {lhapdf_datadir}\n")
            f.write(f"lhapdf_py3 = {lhapdf_config}\n")
    
    def _check_madstr_needed(self) -> bool:
        """Check if MadSTR plugin is needed.
        
        Returns:
            True if MadSTR is needed, False otherwise
        """
        run_card_path = os.path.join(
            self.config.cardsdir, f"{self.config.name}_run_card.dat"
        )
        
        try:
            with open(run_card_path, 'r') as f:
                for line in f:
                    if line.strip().startswith('#'):
                        continue
                    if 'istr' in line and '=' in line:
                        # Extract value from right side of '='
                        try:
                            istr_value = int(line.split('=')[1].split()[0].strip())
                            if 1 <= istr_value <= 6:
                                return True
                            elif istr_value != 0:
                                print("istr should be between 1 and 6")
                                return False
                        except (ValueError, IndexError):
                            # Invalid format, skip
                            continue
        except Exception:
            pass
        
        return False
    
    def _check_5flavor_scheme(self) -> int:
        """Check if 5-flavor scheme is being used.
        
        Returns:
            1 if 5-flavor scheme, 0 otherwise
        """
        logfile = self.config.logfile
        
        if not os.path.exists(logfile):
            return 0
        
        try:
            # Use tail to get last 999 lines
            result = subprocess.run(
                ['tail', '-n', '999', logfile],
                capture_output=True,
                text=True
            )
            
            content = result.stdout
            
            # Check for b~...b or b...b~ patterns
            import re
            if re.search(r'^p *=.*b~.*b', content, re.MULTILINE) or \
               re.search(r'^p *=.*b.*b~', content, re.MULTILINE):
                return 1
        except Exception:
            pass
        
        return 0
    
    def _apply_me_patches(self):
        """Apply matrix element patches if present."""
        patch_script = os.path.join(
            self.config.cardsdir, f"{self.config.name}_patch_me.sh"
        )
        
        if not os.path.exists(patch_script):
            return
        
        print(f"Patching generated matrix element code with {patch_script}")
        
        try:
            subprocess.run(
                ['bash', patch_script, os.path.join(os.getcwd(), self.mg_setup.mg_basedir_orig)],
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Warning: Error applying ME patch: {e}")
    
    def prepare_for_integration(self) -> bool:
        """Prepare process directory for integration.
        
        Returns:
            True if successful, False otherwise
        """
        print("Preparing for integration...")
        
        # Check if process directory exists
        if not os.path.exists(self.config.name):
            print(f"Process output directory {self.config.name} not found.")
            print("Either process generation failed, or the name of the output")
            print(f"did not match the process name {self.config.name} provided to the script.")
            return False
        
        # Determine if scratch space is being used
        is_scratch_space = not os.getcwd().startswith('/afs/')
        
        # Copy or move process directory
        if is_scratch_space:
            print("Moving generated process to working directory")
            shutil.move(self.config.name, 'processtmp')
        else:
            print("Copying generated process to working directory")
            shutil.copytree(self.config.name, 'processtmp')
        
        os.chdir('processtmp')
        
        # Detect NLO mode
        self.is_nlo = os.path.exists('./MCatNLO')
        
        if self.is_nlo:
            print("NLO mode detected")
        else:
            print("LO mode detected")
        
        # Prepare run card
        if not self._prepare_run_card():
            return False
        
        # Copy additional cards
        self._copy_additional_cards()
        
        print("Preparation for integration complete")
        return True
    
    def _prepare_run_card(self) -> bool:
        """Prepare run card with proper PDF settings.
        
        Returns:
            True if successful, False otherwise
        """
        # Find script directory
        script_dir = os.path.join(self.config.prodhome, 'Utilities', 'scripts')
        
        if not os.path.exists(script_dir):
            # Try alternative paths
            if shutil.which('git'):
                try:
                    result = subprocess.run(
                        ['git', 'rev-parse', '--show-toplevel'],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    repo_root = result.stdout.strip()
                    script_dir = os.path.join(repo_root, 'Utilities', 'scripts')
                except:
                    pass
        
        # Call helper function from gridpack_helpers.sh
        # This is complex, so we'll use subprocess to call bash function
        helpers_file = os.path.join(
            os.path.dirname(script_dir), 'gridpack_helpers.sh'
        )
        
        if not os.path.exists(helpers_file):
            # Try MadGraph5_aMCatNLO/Utilities
            helpers_file = os.path.join(
                self.config.prodhome, 'Utilities', 'gridpack_helpers.sh'
            )
        
        if os.path.exists(helpers_file):
            # Source helpers and call prepare_run_card
            # Use shlex.quote to prevent command injection
            import shlex
            
            cmd = (
                f"source {shlex.quote(helpers_file)} && "
                f"prepare_run_card {shlex.quote(self.config.name)} "
                f"{shlex.quote(self.config.cardsdir)} "
                f"{self.is5flavor_scheme} "
                f"{shlex.quote(script_dir)} "
                f"{1 if self.is_nlo else 0}"
            )
            
            try:
                subprocess.run(
                    ['bash', '-c', cmd],
                    check=True,
                    cwd=os.getcwd()
                )
                return True
            except subprocess.CalledProcessError as e:
                print(f"Error preparing run card: {e}")
                return False
        
        # Fallback: just copy run card
        run_card_src = os.path.join(
            self.config.cardsdir, f"{self.config.name}_run_card.dat"
        )
        run_card_dst = os.path.join('Cards', 'run_card.dat')
        
        print("Warning: Could not find gridpack_helpers.sh, copying run card directly")
        shutil.copy(run_card_src, run_card_dst)
        
        return True
    
    def _copy_additional_cards(self):
        """Copy additional card files if present."""
        card_files = [
            ('cuts.f', 'SubProcesses/cuts.f'),
            ('FKS_params.dat', 'Cards/FKS_params.dat'),
            ('setscales.f', 'SubProcesses/setscales.f'),
            ('reweight_xsec.f', 'SubProcesses/reweight_xsec.f'),
            ('reweight_card.dat', 'Cards/reweight_card.dat'),
            ('param_card.dat', 'Cards/param_card.dat'),
            ('madspin_card.dat', 'Cards/madspin_card.dat'),
        ]
        
        for card_name, dest_path in card_files:
            src_path = os.path.join(
                self.config.cardsdir, f"{self.config.name}_{card_name}"
            )
            
            if os.path.exists(src_path):
                print(f"Copying custom {card_name} file")
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy(src_path, dest_path)
