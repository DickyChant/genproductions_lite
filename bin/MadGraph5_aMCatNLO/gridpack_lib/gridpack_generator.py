"""Main gridpack generator orchestrator."""

import os
import sys
import shutil
from pathlib import Path

from .config import GridpackConfig
from .card_validator import CardValidator
from .environment import EnvironmentManager
from .madgraph_setup import MadGraphSetup
from .process_generator import ProcessGenerator
from .tarball_creator import TarballCreator
from .utils import print_system_info, check_git_status, check_lxplus_eos


class GridpackGenerator:
    """Main orchestrator for gridpack generation."""
    
    def __init__(self, config: GridpackConfig):
        """Initialize gridpack generator.
        
        Args:
            config: Gridpack configuration
        """
        self.config = config
        self.card_validator = CardValidator(config)
        self.env_manager = EnvironmentManager(config)
        self.mg_setup = MadGraphSetup(config, self.env_manager)
        self.process_generator = ProcessGenerator(config, self.mg_setup, self.env_manager)
        self.tarball_creator = TarballCreator(config)
    
    def run(self) -> int:
        """Run gridpack generation.
        
        Returns:
            0 on success, non-zero on failure
        """
        try:
            # Print system information
            print_system_info()
            self._print_config()
            
            # Check environment
            check_lxplus_eos()
            
            # Validate cards
            if not self.card_validator.validate_all():
                print("Card validation failed")
                return 1
            
            # Check git status
            check_git_status(self.config.prodhome, self.config.is_cms_connect)
            
            # Execute requested job step
            if self.config.jobstep in ['ALL', 'CODEGEN']:
                if not self._run_codegen():
                    return 1
                
                if self.config.jobstep == 'CODEGEN':
                    print("CODEGEN step complete")
                    return 0
            
            if self.config.jobstep in ['ALL', 'INTEGRATE']:
                if not self._run_integrate():
                    return 1
            
            # Note: MADSPIN step is not yet split from INTEGRATE
            if self.config.jobstep == 'MADSPIN':
                print("MADSPIN hasn't been split from INTEGRATE step yet. Doing nothing.")
                return 0
            
            # Create tarball
            if not self.tarball_creator.create_tarball():
                print("Tarball creation failed")
                return 1
            
            print("Gridpack generation complete!")
            return 0
            
        except Exception as e:
            print(f"Error during gridpack generation: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    def _print_config(self):
        """Print configuration information."""
        print(f"name: {self.config.name}")
        print(f"carddir: {self.config.carddir}")
        print(f"queue: {self.config.queue}")
        print(f"scram_arch: {self.config.scram_arch}")
        print(f"cmssw_version: {self.config.cmssw_version}")
        print(f"jobstep: {self.config.jobstep}")
    
    def _run_codegen(self) -> bool:
        """Run code generation step.
        
        Returns:
            True if successful, False otherwise
        """
        print("\n=== Running CODEGEN step ===\n")
        
        # Check if we need to set up environment
        gridpack_dir = os.path.join(
            self.config.gen_folder, f"{self.config.name}_gridpack"
        )
        
        if not os.path.exists(gridpack_dir):
            # Set up environment
            if not self.env_manager.setup_environment():
                print("Environment setup failed")
                return False
            
            # Set up MadGraph
            if not self.mg_setup.download_and_setup():
                print("MadGraph setup failed")
                return False
        else:
            print(f"Using existing directory {gridpack_dir}")
            
            # Change to work directory
            os.chdir(self.config.workdir)
            
            # Set up SCRAM runtime
            if not self.env_manager._setup_scram_runtime():
                return False
            
            # Set up condor if needed
            if 'condor' in self.config.queue:
                self.env_manager._setup_condor()
        
        # Generate process
        if not self.process_generator.generate_process():
            print("Process generation failed")
            return False
        
        return True
    
    def _run_integrate(self) -> bool:
        """Run integration step.
        
        Returns:
            True if successful, False otherwise
        """
        print("\n=== Running INTEGRATE step ===\n")
        
        # Check if we're reusing existing directory
        if self.config.jobstep == 'INTEGRATE':
            print("Reusing existing directory assuming generated code already exists")
            print("WARNING: If you changed the process card you need to clean the folder and run from scratch")
            
            # Navigate to work directory
            if not os.path.exists(self.config.workdir):
                print(f"Existing directory does not contain expected folder {self.config.workdir}")
                return False
            
            os.chdir(self.config.workdir)
            
            # Set up SCRAM runtime
            if not self.env_manager._setup_scram_runtime():
                return False
            
            # Set up condor if needed
            if 'condor' in self.config.queue:
                self.env_manager._setup_condor()
            
            # Update LHAPDF config
            os.environ['LHAPDF_DATA_PATH'] = self._get_lhapdf_datadir()
        
        # Prepare for integration
        if not self.process_generator.prepare_for_integration():
            print("Preparation for integration failed")
            return False
        
        # Run integration
        if not self._run_pilot_run():
            print("Pilot run failed")
            return False
        
        # Prepare gridpack directory
        if not self._prepare_gridpack():
            print("Gridpack preparation failed")
            return False
        
        return True
    
    def _get_lhapdf_datadir(self) -> str:
        """Get LHAPDF data directory.
        
        Returns:
            Path to LHAPDF data directory
        """
        lhapdf_config = self.env_manager.get_lhapdf_config()
        
        try:
            result = subprocess.run(
                [lhapdf_config, '--datadir'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except:
            return os.environ.get('LHAPDF_DATA_PATH', '')
    
    def _run_pilot_run(self) -> bool:
        """Run pilot integration.
        
        Returns:
            True if successful, False otherwise
        """
        print("Running pilot integration...")
        
        workdir = self.config.workdir
        
        if self.process_generator.is_nlo:
            return self._run_nlo_pilot()
        else:
            return self._run_lo_pilot()
    
    def _run_nlo_pilot(self) -> bool:
        """Run NLO pilot run.
        
        Returns:
            True if successful, False otherwise
        """
        print("Running NLO pilot run...")
        
        # Create makegrid.dat
        makegrid_lines = [
            "shower=OFF",
            "reweight=OFF",
            "done"
        ]
        
        # Add customizecards if present
        customizecards_path = os.path.join(
            self.config.cardsdir, f"{self.config.name}_customizecards.dat"
        )
        
        if os.path.exists(customizecards_path):
            with open(customizecards_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        makegrid_lines.append(line)
            makegrid_lines.append("")
        
        makegrid_lines.append("done")
        
        with open('makegrid.dat', 'w') as f:
            f.write('\n'.join(makegrid_lines) + '\n')
        
        # Run generate_events
        try:
            with open('makegrid.dat', 'r') as f:
                subprocess.run(
                    ['./bin/generate_events', '-n', 'pilotrun'],
                    stdin=f,
                    check=True
                )
        except subprocess.CalledProcessError as e:
            print(f"Error running NLO pilot: {e}")
            return False
        
        # Handle reweighting if needed
        self._handle_reweighting()
        
        # Handle external tarball if needed
        self._handle_external_tarball_nlo()
        
        print("NLO pilot run complete")
        return True
    
    def _run_lo_pilot(self) -> bool:
        """Run LO pilot run.
        
        Returns:
            True if successful, False otherwise
        """
        print("Running LO pilot run...")
        
        # Create makegrid.dat
        makegrid_lines = ["done", "set gridpack True"]
        
        # Add customizecards if present
        customizecards_path = os.path.join(
            self.config.cardsdir, f"{self.config.name}_customizecards.dat"
        )
        
        if os.path.exists(customizecards_path):
            with open(customizecards_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        makegrid_lines.append(line)
            makegrid_lines.append("")
        
        makegrid_lines.append("done")
        
        with open('makegrid.dat', 'w') as f:
            f.write('\n'.join(makegrid_lines) + '\n')
        
        # Run generate_events
        try:
            with open('makegrid.dat', 'r') as f:
                subprocess.run(
                    ['./bin/generate_events', 'pilotrun'],
                    stdin=f,
                    check=True
                )
        except subprocess.CalledProcessError as e:
            print(f"Error running LO pilot: {e}")
            return False
        
        print("LO pilot run complete")
        return True
    
    def _handle_reweighting(self):
        """Handle reweighting preparation if reweight card exists."""
        reweight_card_path = os.path.join(
            self.config.cardsdir, f"{self.config.name}_reweight_card.dat"
        )
        
        if not os.path.exists(reweight_card_path):
            return
        
        print("Preparing reweighting step...")
        
        # Call helper script
        helpers_file = os.path.join(
            self.config.prodhome, 'Utilities', 'gridpack_helpers.sh'
        )
        
        if os.path.exists(helpers_file):
            cmd = f"""
            source {helpers_file}
            prepare_reweight {1 if self.process_generator.is_nlo else 0} {self.config.workdir} {self.config.scram_arch} {reweight_card_path}
            extract_width {1 if self.process_generator.is_nlo else 0} {self.config.workdir} {self.config.cardsdir} {self.config.name}
            """
            
            try:
                subprocess.run(['bash', '-c', cmd], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Warning: Error in reweighting preparation: {e}")
    
    def _handle_external_tarball_nlo(self):
        """Handle external tarball for NLO."""
        external_tarball_card = os.path.join(
            self.config.cardsdir, f"{self.config.name}_externaltarball.dat"
        )
        
        if not os.path.exists(external_tarball_card):
            return
        
        print("Processing external tarball...")
        
        events_file = './Events/pilotrun_decayed_1/events.lhe.gz'
        
        if os.path.exists(events_file):
            # Gunzip events
            subprocess.run(['gunzip', events_file])
            
            # Extract header
            events_lhe = events_file.replace('.gz', '')
            
            with open(events_lhe, 'r') as f:
                content = f.read()
                
                # Extract MG5ProcCard to slha section
                start = content.find('<MG5ProcCard>')
                end = content.find('</slha>') + len('</slha>')
                
                if start != -1 and end != -1:
                    header = content[start:end]
                    
                    header_file = os.path.join(self.config.workdir, 'header_for_madspin.txt')
                    with open(header_file, 'w') as hf:
                        hf.write(header)
            
            # Gzip events again
            subprocess.run(['gzip', events_lhe])
    
    def _prepare_gridpack(self) -> bool:
        """Prepare final gridpack directory.
        
        Returns:
            True if successful, False otherwise
        """
        print("Preparing gridpack directory...")
        
        workdir = self.config.workdir
        os.chdir(workdir)
        
        # Clean up old gridpack directory
        if os.path.exists('gridpack'):
            shutil.rmtree('gridpack')
        
        os.makedirs('gridpack')
        
        if self.process_generator.is_nlo:
            return self._prepare_nlo_gridpack()
        else:
            return self._prepare_lo_gridpack()
    
    def _prepare_nlo_gridpack(self) -> bool:
        """Prepare NLO gridpack.
        
        Returns:
            True if successful, False otherwise
        """
        workdir = self.config.workdir
        
        # Update configuration
        config_file = './Cards/amcatnlo_configuration.txt'
        with open(config_file, 'a') as f:
            f.write("mg5_path = ../mgbasedir\n")
            f.write("cluster_temp_path = None\n")
        
        # Move process to gridpack
        shutil.move('processtmp', 'gridpack/process')
        
        # Copy MadGraph basedir
        mg_basedir_src = os.path.join(workdir, self.mg_setup.mg_basedir_orig)
        mg_basedir_dst = 'gridpack/mgbasedir'
        shutil.copytree(mg_basedir_src, mg_basedir_dst)
        
        os.chdir('gridpack')
        
        # Copy runcmsgrid script
        runcmsgrid_src = os.path.join(self.config.prodhome, 'runcmsgrid_NLO.sh')
        shutil.copy(runcmsgrid_src, './runcmsgrid.sh')
        
        # Copy external tarball header if needed
        external_tarball_card = os.path.join(
            self.config.cardsdir, f"{self.config.name}_externaltarball.dat"
        )
        
        if os.path.exists(external_tarball_card):
            header_src = os.path.join(workdir, 'header_for_madspin.txt')
            if os.path.exists(header_src):
                shutil.copy(header_src, './')
        
        self._finalize_gridpack()
        
        return True
    
    def _prepare_lo_gridpack(self) -> bool:
        """Prepare LO gridpack.
        
        Returns:
            True if successful, False otherwise
        """
        workdir = self.config.workdir
        
        # Move and unpack gridpack
        gridpack_archive = os.path.join(workdir, 'processtmp', 'pilotrun_gridpack.tar.gz')
        
        if os.path.exists(gridpack_archive):
            shutil.move(gridpack_archive, workdir)
        
        # Clean up processtmp
        processtmp = os.path.join(workdir, 'processtmp')
        if os.path.exists(processtmp):
            shutil.rmtree(processtmp)
        
        # Create process directory and unpack
        os.makedirs('process')
        os.chdir('process')
        
        subprocess.run(
            ['tar', '-xzf', '../pilotrun_gridpack.tar.gz'],
            check=True
        )
        
        os.remove('../pilotrun_gridpack.tar.gz')
        
        # Generate a few events manually (as of mg29x)
        subprocess.run(['./run.sh', '1000', '234567'])
        
        unweighted_events = os.path.join(workdir, 'unweighted_events.lhe.gz')
        shutil.move('events.lhe.gz', unweighted_events)
        
        # Handle reweighting
        self._handle_reweighting()
        
        # Handle madspin
        self._handle_madspin_lo()
        
        # Update configuration
        config_file = './madevent/Cards/me5_configuration.txt'
        with open(config_file, 'a') as f:
            f.write("mg5_path = ../../mgbasedir\n")
            f.write("cluster_temp_path = None\n")
            f.write("run_mode = 0\n")
        
        os.chdir(workdir)
        
        # Move to gridpack
        shutil.move('process', 'gridpack/process')
        
        # Copy MadGraph basedir
        mg_basedir_src = os.path.join(workdir, self.mg_setup.mg_basedir_orig)
        mg_basedir_dst = 'gridpack/mgbasedir'
        shutil.copytree(mg_basedir_src, mg_basedir_dst)
        
        os.chdir('gridpack')
        
        # Copy runcmsgrid script
        runcmsgrid_src = os.path.join(self.config.prodhome, 'runcmsgrid_LO.sh')
        shutil.copy(runcmsgrid_src, './runcmsgrid.sh')
        
        self._finalize_gridpack()
        
        return True
    
    def _handle_madspin_lo(self):
        """Handle madspin for LO mode."""
        madspin_card_path = os.path.join(
            self.config.cardsdir, f"{self.config.name}_madspin_card.dat"
        )
        
        if not os.path.exists(madspin_card_path):
            return
        
        print("Running madspin...")
        
        workdir = self.config.workdir
        unweighted_events = os.path.join(workdir, 'unweighted_events.lhe.gz')
        
        # Create madspin run file
        madspinrun_lines = [f"import {unweighted_events}"]
        
        with open(madspin_card_path, 'r') as f:
            madspinrun_lines.extend(f.readlines())
        
        with open('madspinrun.dat', 'w') as f:
            f.writelines(madspinrun_lines)
        
        # Run madspin
        madspin_bin = os.path.join(
            workdir, self.mg_setup.mg_basedir_orig,
            'MadSpin', 'madspin'
        )
        
        try:
            subprocess.run([madspin_bin, 'madspinrun.dat'], check=True)
            
            # Clean up
            os.remove('madspinrun.dat')
            
            # Remove tmp directories
            import glob
            for tmpdir in glob.glob('tmp*'):
                if os.path.isdir(tmpdir):
                    shutil.rmtree(tmpdir)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Error running madspin: {e}")
    
    def _finalize_gridpack(self):
        """Finalize gridpack preparation."""
        # Update runcmsgrid.sh with proper values
        self._update_runcmsgrid()
        
        # Clean unneeded files
        self._clean_gridpack()
        
        # Handle external tarball
        self._handle_external_tarball_final()
        
        # Copy merge.pl
        merge_pl_src = os.path.join(self.config.prodhome, 'Utilities', 'merge.pl')
        if os.path.exists(merge_pl_src):
            shutil.copy(merge_pl_src, './')
    
    def _update_runcmsgrid(self):
        """Update runcmsgrid.sh with configuration."""
        runcmsgrid = './runcmsgrid.sh'
        
        if not os.path.exists(runcmsgrid):
            return
        
        # Read file
        with open(runcmsgrid, 'r') as f:
            content = f.read()
        
        # Replace placeholders
        content = content.replace('SCRAM_ARCH_VERSION_REPLACE', self.config.scram_arch)
        content = content.replace('CMSSW_VERSION_REPLACE', self.config.cmssw_version)
        
        # Get PDF sets
        pdf_extra_args = ""
        if self.process_generator.is5flavor_scheme == 1:
            pdf_extra_args = "--is5FlavorScheme"
        
        script_dir = os.path.join(self.config.prodhome, 'Utilities', 'scripts')
        
        try:
            result = subprocess.run(
                ['python3', os.path.join(script_dir, 'getMG5_aMC_PDFInputs.py'),
                 '-f', 'systematics', '-c', 'run3'] + ([pdf_extra_args] if pdf_extra_args else []),
                capture_output=True,
                text=True,
                check=True
            )
            pdf_sys_args = result.stdout.strip()
            content = content.replace('PDF_SETS_REPLACE', pdf_sys_args)
        except Exception as e:
            print(f"Warning: Could not get PDF sets: {e}")
        
        # Write file
        with open(runcmsgrid, 'w') as f:
            f.write(content)
    
    def _clean_gridpack(self):
        """Clean unneeded files from gridpack."""
        helpers_dir = os.path.join(self.config.prodhome, 'Utilities')
        clean_script = os.path.join(helpers_dir, 'cleangridmore.sh')
        
        if os.path.exists(clean_script):
            try:
                subprocess.run(['bash', clean_script], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Warning: Error cleaning gridpack: {e}")
    
    def _handle_external_tarball_final(self):
        """Handle external tarball in final gridpack."""
        external_tarball_card = os.path.join(
            self.config.cardsdir, f"{self.config.name}_externaltarball.dat"
        )
        
        if not os.path.exists(external_tarball_card):
            return
        
        print("Locating the external tarball...")
        
        # Copy external tarball card
        shutil.copy(external_tarball_card, './')
        
        # Source and get EXTERNAL_TARBALL variable
        # This is a bit tricky in Python, we'll parse the file
        with open(f"{self.config.name}_externaltarball.dat", 'r') as f:
            for line in f:
                if 'EXTERNAL_TARBALL' in line and '=' in line:
                    external_tarball = line.split('=')[1].strip().strip('"').strip("'")
                    print(f"External tarball: {external_tarball}")
                    
                    if os.path.exists(external_tarball):
                        # Copy and extract tarball
                        tarball_name = os.path.basename(external_tarball)
                        shutil.copy(external_tarball, './')
                        
                        os.makedirs('external_tarball', exist_ok=True)
                        os.chdir('external_tarball')
                        
                        subprocess.run(['tar', '-xvaf', f'../{tarball_name}'])
                        
                        os.chdir('..')
                        os.remove(tarball_name)
                    
                    break


import subprocess
