# Directories
rsync -avc --delete cli/ ../Commit/ELK_packages/escmd/cli/
rsync -avc --delete commands/ ../Commit/ELK_packages/escmd/commands/
rsync -avc --delete display/ ../Commit/ELK_packages/escmd/display/
rsync -avc --delete docs/ ../Commit/ELK_packages/escmd/docs/
rsync -avc --delete examples/ ../Commit/ELK_packages/escmd/examples/
rsync -avc --delete handlers/ ../Commit/ELK_packages/escmd/handlers/
rsync -avc --delete metrics/ ../Commit/ELK_packages/escmd/metrics/
rsync -avc --delete processors/ ../Commit/ELK_packages/escmd/processors/
rsync -avc --delete reports/ ../Commit/ELK_packages/escmd/reports/
rsync -avc --delete security/ ../Commit/ELK_packages/escmd/security/
rsync -avc --delete tests/ ../Commit/ELK_packages/escmd/tests/
rsync -avc --delete esterm_modules/ ../Commit/ELK_packages/escmd/esterm_modules/
rsync -avc --delete template_utils/ ../Commit/ELK_packages/escmd/template_utils/

# Core Python modules
cp escmd.py ../Commit/ELK_packages/escmd/escmd.py
cp esterm.py ../Commit/ELK_packages/escmd/esterm.py
cp configuration_manager.py ../Commit/ELK_packages/escmd/configuration_manager.py
cp command_handler.py ../Commit/ELK_packages/escmd/command_handler.py
cp esclient.py ../Commit/ELK_packages/escmd/esclient.py
cp unfreeze_index.py ../Commit/ELK_packages/escmd/unfreeze_index.py
cp error_handling.py ../Commit/ELK_packages/escmd/error_handling.py
cp logging_config.py ../Commit/ELK_packages/escmd/logging_config.py
cp utils.py ../Commit/ELK_packages/escmd/utils.py
cp performance.py ../Commit/ELK_packages/escmd/performance.py

# Configuration files
cp escmd.yml ../Commit/ELK_packages/escmd/escmd.yml
cp esterm_config.yml ../Commit/ELK_packages/escmd/esterm_config.yml
cp esterm_themes.yml ../Commit/ELK_packages/escmd/esterm_themes.yml
cp themes.yml ../Commit/ELK_packages/escmd/themes.yml
cp s3snapshot_repo_mapping.yml ../Commit/ELK_packages/escmd/s3snapshot_repo_mapping.yml

# Launchers and wrappers
cp esterm ../Commit/ELK_packages/escmd/esterm
cp escmd_wrapper.sh ../Commit/ELK_packages/escmd/escmd_wrapper.sh

# Dependency files
cp requirements.txt ../Commit/ELK_packages/escmd/requirements.txt
cp requirements-py36.txt ../Commit/ELK_packages/escmd/requirements-py36.txt
cp requirements-test.txt ../Commit/ELK_packages/escmd/requirements-test.txt
