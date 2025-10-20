"""
Security Manager for API Keys and Sensitive Data
Encrypted storage, key vault integration, and secure credential management
"""

import os
import json
import base64
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import secrets

from logger import setup_logger

logger = setup_logger('security_manager')


class SecurityManager:
    """
    Secure credential and API key management with encryption
    """
    
    def __init__(
        self,
        encryption_key: Optional[str] = None,
        key_file: str = '.secret_key',
        encrypted_env_file: str = '.env.encrypted',
        master_password: Optional[str] = None
    ):
        """
        Initialize security manager
        
        Args:
            encryption_key: Base64 encoded encryption key
            key_file: Path to store encryption key
            encrypted_env_file: Path to encrypted environment file
            master_password: Master password for key derivation
        """
        self.key_file = Path(key_file)
        self.encrypted_env_file = Path(encrypted_env_file)
        self.master_password = master_password
        
        # Load or generate encryption key
        if encryption_key:
            self.encryption_key = encryption_key.encode()
        else:
            self.encryption_key = self._load_or_generate_key()
        
        self.fernet = Fernet(self.encryption_key)
        
        # In-memory credential store
        self.credentials: Dict[str, str] = {}
        
        # API key rotation tracking
        self.key_rotation_log: Dict[str, datetime] = {}
    
    def _load_or_generate_key(self) -> bytes:
        """Load encryption key from file or generate new one"""
        try:
            if self.key_file.exists():
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                logger.info("Loaded existing encryption key")
                return key
            else:
                # Generate new key
                if self.master_password:
                    key = self._derive_key_from_password(self.master_password)
                else:
                    key = Fernet.generate_key()
                
                # Save key securely
                self.key_file.parent.mkdir(exist_ok=True)
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                
                # Set file permissions (Unix only)
                if os.name != 'nt':  # Not Windows
                    os.chmod(self.key_file, 0o600)
                
                logger.info("Generated new encryption key")
                return key
                
        except Exception as e:
            logger.exception(f"Error loading/generating encryption key: {e}")
            raise
    
    def _derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """
        Derive encryption key from password using PBKDF2
        
        Args:
            password: Master password
            salt: Salt for key derivation (generated if None)
            
        Returns:
            Derived encryption key
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt_string(self, plaintext: str) -> str:
        """
        Encrypt a string
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64 encoded encrypted string
        """
        try:
            encrypted = self.fernet.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.exception(f"Error encrypting string: {e}")
            raise
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """
        Decrypt a string
        
        Args:
            encrypted_text: Base64 encoded encrypted string
            
        Returns:
            Decrypted plaintext
        """
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted = self.fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.exception(f"Error decrypting string: {e}")
            raise
    
    def store_credential(self, key: str, value: str, persist: bool = True):
        """
        Store credential in memory and optionally persist encrypted
        
        Args:
            key: Credential key (e.g., 'BINANCE_API_KEY')
            value: Credential value
            persist: Save to encrypted file
        """
        try:
            # Store in memory
            self.credentials[key] = value
            
            if persist:
                self._save_encrypted_credentials()
            
            logger.info(f"Stored credential: {key}")
            
        except Exception as e:
            logger.exception(f"Error storing credential: {e}")
    
    def get_credential(self, key: str) -> Optional[str]:
        """
        Retrieve credential from memory
        
        Args:
            key: Credential key
            
        Returns:
            Credential value or None
        """
        return self.credentials.get(key)
    
    def _save_encrypted_credentials(self):
        """Save credentials to encrypted file"""
        try:
            # Convert to JSON
            json_data = json.dumps(self.credentials)
            
            # Encrypt
            encrypted_data = self.fernet.encrypt(json_data.encode())
            
            # Save to file
            with open(self.encrypted_env_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set file permissions
            if os.name != 'nt':
                os.chmod(self.encrypted_env_file, 0o600)
            
            logger.info(f"Saved {len(self.credentials)} encrypted credentials")
            
        except Exception as e:
            logger.exception(f"Error saving encrypted credentials: {e}")
    
    def load_encrypted_credentials(self) -> Dict[str, str]:
        """
        Load credentials from encrypted file
        
        Returns:
            Dictionary of credentials
        """
        try:
            if not self.encrypted_env_file.exists():
                logger.warning("Encrypted credentials file not found")
                return {}
            
            # Read encrypted data
            with open(self.encrypted_env_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt
            decrypted_data = self.fernet.decrypt(encrypted_data)
            
            # Parse JSON
            credentials = json.loads(decrypted_data.decode())
            
            # Store in memory
            self.credentials.update(credentials)
            
            logger.info(f"Loaded {len(credentials)} encrypted credentials")
            return credentials
            
        except Exception as e:
            logger.exception(f"Error loading encrypted credentials: {e}")
            return {}
    
    def load_from_env(self, env_file: str = '.env'):
        """
        Load credentials from .env file and encrypt them
        
        Args:
            env_file: Path to .env file
        """
        try:
            env_path = Path(env_file)
            if not env_path.exists():
                logger.warning(f".env file not found: {env_file}")
                return
            
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        self.store_credential(key, value, persist=False)
            
            # Save encrypted version
            self._save_encrypted_credentials()
            
            logger.info(f"Loaded credentials from {env_file}")
            
        except Exception as e:
            logger.exception(f"Error loading from .env: {e}")
    
    def generate_api_key(self, length: int = 32) -> str:
        """
        Generate secure random API key
        
        Args:
            length: Key length in bytes
            
        Returns:
            Hex-encoded API key
        """
        return secrets.token_hex(length)
    
    def rotate_api_key(self, key_name: str, new_key: str):
        """
        Rotate API key and log rotation
        
        Args:
            key_name: Name of the API key
            new_key: New API key value
        """
        old_key = self.credentials.get(key_name)
        
        if old_key:
            # Log rotation
            self.key_rotation_log[key_name] = datetime.now()
            logger.info(f"API key rotated: {key_name}")
        
        # Store new key
        self.store_credential(key_name, new_key)
    
    def check_key_rotation_needed(
        self,
        key_name: str,
        rotation_days: int = 90
    ) -> bool:
        """
        Check if API key rotation is needed
        
        Args:
            key_name: Name of the API key
            rotation_days: Days between rotations
            
        Returns:
            True if rotation needed
        """
        if key_name not in self.key_rotation_log:
            return True
        
        last_rotation = self.key_rotation_log[key_name]
        days_since_rotation = (datetime.now() - last_rotation).days
        
        if days_since_rotation >= rotation_days:
            logger.warning(
                f"Key rotation recommended for {key_name} "
                f"({days_since_rotation} days since last rotation)"
            )
            return True
        
        return False
    
    def validate_api_key_format(self, api_key: str, min_length: int = 32) -> bool:
        """
        Validate API key format
        
        Args:
            api_key: API key to validate
            min_length: Minimum key length
            
        Returns:
            True if valid
        """
        if not api_key or len(api_key) < min_length:
            return False
        
        # Check for common weak patterns
        weak_patterns = ['test', '1234', 'abcd', 'password', 'key']
        if any(pattern in api_key.lower() for pattern in weak_patterns):
            logger.warning("API key contains weak pattern")
            return False
        
        return True
    
    def mask_sensitive_data(self, text: str, keys_to_mask: Optional[list] = None) -> str:
        """
        Mask sensitive data in text/logs
        
        Args:
            text: Text containing sensitive data
            keys_to_mask: List of credential keys to mask
            
        Returns:
            Text with masked sensitive data
        """
        if keys_to_mask is None:
            keys_to_mask = list(self.credentials.keys())
        
        masked_text = text
        for key in keys_to_mask:
            value = self.credentials.get(key)
            if value and value in masked_text:
                # Show first 4 and last 4 characters
                if len(value) > 8:
                    mask = value[:4] + '****' + value[-4:]
                else:
                    mask = '****'
                masked_text = masked_text.replace(value, mask)
        
        return masked_text
    
    def create_backup(self, backup_path: Optional[str] = None):
        """
        Create encrypted backup of credentials
        
        Args:
            backup_path: Path for backup file
        """
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f'.env.backup_{timestamp}.encrypted'
            
            backup_path = Path(backup_path)
            
            # Save encrypted credentials
            json_data = json.dumps(self.credentials)
            encrypted_data = self.fernet.encrypt(json_data.encode())
            
            with open(backup_path, 'wb') as f:
                f.write(encrypted_data)
            
            if os.name != 'nt':
                os.chmod(backup_path, 0o600)
            
            logger.info(f"Created encrypted backup: {backup_path}")
            
        except Exception as e:
            logger.exception(f"Error creating backup: {e}")
    
    def restore_from_backup(self, backup_path: str):
        """
        Restore credentials from encrypted backup
        
        Args:
            backup_path: Path to backup file
        """
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return
            
            with open(backup_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.fernet.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            
            self.credentials.update(credentials)
            self._save_encrypted_credentials()
            
            logger.info(f"Restored {len(credentials)} credentials from backup")
            
        except Exception as e:
            logger.exception(f"Error restoring from backup: {e}")
    
    def get_security_audit_report(self) -> Dict:
        """
        Generate security audit report
        
        Returns:
            Dictionary with security metrics
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_credentials': len(self.credentials),
            'encrypted_file_exists': self.encrypted_env_file.exists(),
            'key_file_permissions': None,
            'keys_needing_rotation': [],
            'weak_keys': []
        }
        
        # Check file permissions
        if self.key_file.exists() and os.name != 'nt':
            stat_info = os.stat(self.key_file)
            report['key_file_permissions'] = oct(stat_info.st_mode)[-3:]
        
        # Check key rotation
        for key_name in self.credentials.keys():
            if self.check_key_rotation_needed(key_name):
                report['keys_needing_rotation'].append(key_name)
        
        # Check weak keys
        for key_name, key_value in self.credentials.items():
            if not self.validate_api_key_format(key_value):
                report['weak_keys'].append(key_name)
        
        return report


class AzureKeyVaultIntegration:
    """
    Integration with Azure Key Vault for production deployments
    """
    
    def __init__(self, vault_url: str, credential=None):
        """
        Initialize Azure Key Vault client
        
        Args:
            vault_url: Azure Key Vault URL
            credential: Azure credential (DefaultAzureCredential recommended)
        """
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import DefaultAzureCredential
            
            if credential is None:
                credential = DefaultAzureCredential()
            
            self.client = SecretClient(vault_url=vault_url, credential=credential)
            logger.info(f"Connected to Azure Key Vault: {vault_url}")
            
        except ImportError:
            logger.error("Azure SDK not installed. Install with: pip install azure-keyvault-secrets azure-identity")
            self.client = None
        except Exception as e:
            logger.exception(f"Error connecting to Azure Key Vault: {e}")
            self.client = None
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve secret from Key Vault
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            Secret value or None
        """
        if self.client is None:
            return None
        
        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            logger.exception(f"Error retrieving secret {secret_name}: {e}")
            return None
    
    def set_secret(self, secret_name: str, secret_value: str):
        """
        Store secret in Key Vault
        
        Args:
            secret_name: Name of the secret
            secret_value: Secret value
        """
        if self.client is None:
            return
        
        try:
            self.client.set_secret(secret_name, secret_value)
            logger.info(f"Secret stored in Key Vault: {secret_name}")
        except Exception as e:
            logger.exception(f"Error storing secret {secret_name}: {e}")


# Example usage
if __name__ == '__main__':
    # Initialize security manager
    sec_mgr = SecurityManager(master_password='my_secure_password_123')
    
    # Store credentials
    sec_mgr.store_credential('BINANCE_API_KEY', 'abc123xyz789')
    sec_mgr.store_credential('BINANCE_API_SECRET', 'secret456secret')
    sec_mgr.store_credential('TELEGRAM_BOT_TOKEN', 'bot_token_here')
    
    # Retrieve credential
    api_key = sec_mgr.get_credential('BINANCE_API_KEY')
    print(f"API Key: {api_key}")
    
    # Mask sensitive data
    log_message = "API call with key: abc123xyz789"
    masked = sec_mgr.mask_sensitive_data(log_message)
    print(f"Masked: {masked}")
    
    # Create backup
    sec_mgr.create_backup()
    
    # Security audit
    audit = sec_mgr.get_security_audit_report()
    print(f"\nSecurity Audit:")
    print(f"  Total credentials: {audit['total_credentials']}")
    print(f"  Keys needing rotation: {audit['keys_needing_rotation']}")
    print(f"  Weak keys: {audit['weak_keys']}")
