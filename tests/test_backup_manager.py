import os
import shutil
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import sys

# Add the parent directory to sys.path so Python can find src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backup_manager import (
    BackupConfig, BackupCommand, EncryptCommand, 
    DecryptCommand, ExtractCommand, CleanupCommand, 
    SizeCalculator, ContextManager, BackupFacade
)

# Fixtures
@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing that gets cleaned up afterwards"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration for backup manager"""
    config = BackupConfig()
    config.backup_folder = os.path.join(temp_dir, "backups")
    config.config_dir = os.path.join(temp_dir, "config")
    config.dirs_to_backup = [os.path.join(temp_dir, "test_data")]
    config.ignore_list = [os.path.join(temp_dir, "test_data/ignored")]
    os.makedirs(config.backup_folder, exist_ok=True)
    os.makedirs(config.config_dir, exist_ok=True)
    return config

@pytest.fixture
def test_backup_files(test_config):
    """Create test backup files for testing"""
    os.makedirs(test_config.backup_folder, exist_ok=True)
    # Create a few sample backup files with different dates
    backup_files = [
        "01-01-2022.tar.xz",
        "02-01-2022.tar.xz",
        "03-01-2022.tar.xz",
        "01-01-2022.tar.xz.enc",
        "02-01-2022.tar.xz.enc"
    ]
    for filename in backup_files:
        with open(os.path.join(test_config.backup_folder, filename), "w") as f:
            f.write("test backup content")
    return backup_files

@pytest.fixture
def test_data_dir(temp_dir):
    """Create test data for backup"""
    data_dir = os.path.join(temp_dir, "test_data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Create some test files
    with open(os.path.join(data_dir, "file1.txt"), "w") as f:
        f.write("Test file 1 content")
    
    with open(os.path.join(data_dir, "file2.txt"), "w") as f:
        f.write("Test file 2 content")
    
    # Create a directory to be ignored
    ignore_dir = os.path.join(data_dir, "ignored")
    os.makedirs(ignore_dir, exist_ok=True)
    with open(os.path.join(ignore_dir, "ignored.txt"), "w") as f:
        f.write("This file should be ignored")
    
    return data_dir

class TestBackupConfig:
    def test_init_expands_paths(self):
        """Test that paths are expanded in __post_init__"""
        with patch('os.path.expanduser', return_value='/expanded/path'):
            config = BackupConfig(
                backup_folder="~/test",
                config_dir="~/.config",
                dirs_to_backup=["~/dir1"],
                ignore_list=["~/ignore"]
            )
            
            assert config.backup_folder == '/expanded/path'
            assert config.config_dir == '/expanded/path'
            assert config.dirs_to_backup == ['/expanded/path']
            assert config.ignore_list == ['/expanded/path']
    
    def test_save_config(self, test_config, temp_dir):
        """Test saving configuration to file"""
        test_config.save()
        
        # Check if the config file was created
        config_path = os.path.join(test_config.config_dir, "config.json")
        assert os.path.exists(config_path)
        
        # Verify content
        with open(config_path, 'r') as f:
            data = json.load(f)
            assert data["backup_folder"] == test_config.backup_folder
            assert data["dirs_to_backup"] == test_config.dirs_to_backup
    
    def test_load_config(self, test_config):
        """Test loading configuration from file"""
        # Prepare the config data as it would be in the file
        config_data = {
            "backup_folder": test_config.backup_folder,
            "config_dir": test_config.config_dir,
            "keep_backup": test_config.keep_backup,
            "keep_enc_backup": test_config.keep_enc_backup,
            "dirs_to_backup": test_config.dirs_to_backup,
            "ignore_list": test_config.ignore_list,
            "last_backup": test_config.last_backup,
        }
        
        # Create a mock file object that returns our config data
        mock_file = mock_open(read_data=json.dumps(config_data))
        
        # Patch 'open' to return our mock file
        with patch('builtins.open', mock_file):
            # Ensure os.path.exists returns True for any config path
            with patch('os.path.exists', return_value=True):
                loaded_config = BackupConfig.load()
        
        # Check if loaded correctly
        assert loaded_config.backup_folder == test_config.backup_folder
        assert loaded_config.dirs_to_backup == test_config.dirs_to_backup
    
    def test_verify_config_valid(self, test_config, test_data_dir):
        """Test configuration verification when valid"""
        # Prepare the config data as it would be in the file
        config_data = {
            "backup_folder": test_config.backup_folder,
            "config_dir": test_config.config_dir,
            "keep_backup": test_config.keep_backup,
            "keep_enc_backup": test_config.keep_enc_backup,
            "dirs_to_backup": test_config.dirs_to_backup,
            "ignore_list": test_config.ignore_list,
            "last_backup": test_config.last_backup,
        }
        
        # Create a mock file object that returns our config data
        mock_file = mock_open(read_data=json.dumps(config_data))
        
        # Patch 'open' to return our mock file and ensure paths exist
        with patch('builtins.open', mock_file), patch('os.path.exists', return_value=True):
            valid, message = BackupConfig.verify_config()
            assert valid
            assert "valid" in message.lower()
    
    @patch('os.path.exists', return_value=False)
    def test_verify_config_missing(self, mock_exists):
        """Test config verification when config file is missing"""
        valid, message = BackupConfig.verify_config()
        assert not valid
        assert "not found" in message.lower()
    

# Tests for SizeCalculator
class TestSizeCalculator:
    def test_calculate_total_size(self, test_data_dir, test_config):
        """Test size calculation functionality"""
        with patch('builtins.print'):  # Suppress print outputs
            calculator = SizeCalculator(
                directories=[test_data_dir],
                ignore_list=[os.path.join(test_data_dir, "ignored")]
            )
            total_size = calculator.calculate_total_size()
            
            # We should only count the sizes of file1.txt and file2.txt
            expected_size = os.path.getsize(os.path.join(test_data_dir, "file1.txt")) + \
                            os.path.getsize(os.path.join(test_data_dir, "file2.txt"))
            
            assert total_size == expected_size
    
    def test_should_ignore(self, test_data_dir):
        """Test path ignoring logic"""
        calculator = SizeCalculator(
            directories=[test_data_dir],
            ignore_list=[os.path.join(test_data_dir, "ignored")]
        )
        
        # This path should be ignored
        assert calculator._should_ignore(os.path.join(test_data_dir, "ignored", "file.txt"))
        
        # This path should not be ignored
        assert not calculator._should_ignore(os.path.join(test_data_dir, "file1.txt"))

# Tests for Commands
class TestBackupCommand:
    @patch('subprocess.run')
    @patch('os.cpu_count', return_value=4)
    def test_execute_backup(self, mock_cpu_count, mock_run, test_config, test_data_dir):
        """Test backup execution"""
        with patch('builtins.print'), patch.object(SizeCalculator, 'calculate_total_size', return_value=1024):
            command = BackupCommand(test_config)
            result = command.execute()
            
            # Check the command was executed
            assert mock_run.called
            assert result is True
    
    @patch('os.path.exists', return_value=True)
    @patch('builtins.input', return_value='y')
    @patch('os.remove')
    def test_execute_backup_file_exists(self, mock_remove, mock_input, mock_exists, test_config):
        """Test backup when output file already exists"""
        with patch('subprocess.run'), patch.object(SizeCalculator, 'calculate_total_size', return_value=1024), patch('builtins.print'):
            command = BackupCommand(test_config)
            command._run_backup_process(1024)
            
            # Check file was removed
            assert mock_remove.called

class TestEncryptCommand:
    @patch('subprocess.run')
    @patch('getpass.getpass', return_value='password123')
    def test_encryption(self, mock_getpass, mock_run, test_config, temp_dir):
        """Test encryption command"""
        test_file = os.path.join(temp_dir, "test.tar.xz")
        with open(test_file, 'w') as f:
            f.write("test content")
            
        command = EncryptCommand(test_config, test_file)
        
        # Mock subprocess run to return success
        mock_run.return_value = MagicMock(stderr=b"")
        
        result = command.execute()
        assert result is True
        assert mock_run.called
    
    @patch('os.path.isfile', return_value=False)
    def test_encryption_missing_file(self, mock_isfile, test_config):
        """Test encryption with missing input file"""
        command = EncryptCommand(test_config, "nonexistent.tar.xz")
        result = command.execute()
        assert result is False

class TestCleanupCommand:
    def test_cleanup(self, test_config, test_backup_files):
        """Test cleanup of old backups"""
        command = CleanupCommand(test_config)
        
        # Set to keep only the newest file
        test_config.keep_backup = 1
        test_config.keep_enc_backup = 1
        
        with patch('builtins.print'):
            command.execute()
        
        # Check that only the newest files remain
        remaining_files = os.listdir(test_config.backup_folder)
        assert len([f for f in remaining_files if f.endswith('.tar.xz')]) == 1
        assert len([f for f in remaining_files if f.endswith('.tar.xz.enc')]) == 1
        
        # Verify we kept the newest ones
        assert "03-01-2022.tar.xz" in remaining_files
        assert "02-01-2022.tar.xz.enc" in remaining_files

# Tests for ContextManager
class TestContextManager:
    @patch('getpass.getpass', return_value='test_password')
    def test_password_context(self, mock_getpass):
        """Test secure password handling context"""
        manager = ContextManager()
        
        with manager._password_context() as password:
            assert password == 'test_password'
        
        # After context exit, password should be securely wiped
        # This is hard to test directly as we're testing the absence of data
        pass

# Tests for BackupFacade
class TestBackupFacade:
    @patch.object(BackupConfig, 'load')
    def test_init(self, mock_load, test_config):
        """Test facade initialization"""
        mock_load.return_value = test_config
        facade = BackupFacade()
        
        assert isinstance(facade.commands["backup"], BackupCommand)
        assert isinstance(facade.commands["cleanup"], CleanupCommand)
    
    @patch('builtins.input', side_effect=['test_path', '2', '3', '1', 'dir1,dir2', '3', '1', 'ignore1', '3'])
    def test_configure(self, mock_input, temp_dir):
        """Test interactive configuration"""
        with patch.object(BackupConfig, 'save'), patch('os.path.exists', return_value=True), patch('builtins.print'):
            facade = BackupFacade()
            facade.configure()
            
            assert 'test_path' in facade.config.backup_folder
            assert 'dir1' in facade.config.dirs_to_backup
            assert 'dir2' in facade.config.dirs_to_backup
            assert 'ignore1' in facade.config.ignore_list
    
    @patch.object(BackupCommand, 'execute')
    def test_execute_command(self, mock_execute):
        """Test command execution through facade"""
        facade = BackupFacade()
        facade.execute_command("backup")
        
        assert mock_execute.called
    
    def test_execute_invalid_command(self):
        """Test execution of invalid command"""
        facade = BackupFacade()
        with pytest.raises(ValueError):
            facade.execute_command("invalid_command")

if __name__ == "__main__":
    pytest.main()