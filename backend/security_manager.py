import os
import base64
import logging
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self):
        # Master key must be 32 bytes for AES-256
        key_b64 = os.environ.get("INDICPDF_MASTER_KEY")
        
        if key_b64:
            try:
                self.key = base64.b64decode(key_b64)
                if len(self.key) != 32:
                    logger.warning("INDICPDF_MASTER_KEY is not 32 bytes. Using first 32 bytes or padding.")
                    self.key = self.key[:32].ljust(32, b'\0')
            except Exception as e:
                logger.error(f"Failed to decode INDICPDF_MASTER_KEY: {e}")
                self.key = os.urandom(32) # Fallback to prevent crash, but breaks persistence
        else:
            logger.warning("INDICPDF_MASTER_KEY not found in environment. Generating a transient key.")
            self.key = os.urandom(32)
            
        self.aesgcm = AESGCM(self.key)

    def encrypt_file(self, plaintext_path: Path, ciphertext_path: Path):
        """Encrypt a file from disk and save the ciphertext."""
        try:
            with open(plaintext_path, "rb") as f:
                data = f.read()
            
            nonce = os.urandom(12)
            # AES-256-GCM: nonce + ciphertext + tag
            ciphertext = self.aesgcm.encrypt(nonce, data, None)
            
            with open(ciphertext_path, "wb") as f:
                f.write(nonce + ciphertext)
            
            # Shred the plaintext immediately if it was a temp file on disk
            # (In our pipeline, we try to avoid writing plaintext to disk at all)
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt_to_memory(self, ciphertext_path: Path) -> bytes:
        """Decrypt a file into memory."""
        try:
            with open(ciphertext_path, "rb") as f:
                raw_data = f.read()
            
            nonce = raw_data[:12]
            ciphertext = raw_data[12:]
            
            return self.aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def decrypt_to_file(self, ciphertext_path: Path, output_path: Path):
        """Decrypt a file back to disk (use sparingly for processing)."""
        try:
            plaintext = self.decrypt_to_memory(ciphertext_path)
            with open(output_path, "wb") as f:
                f.write(plaintext)
        except Exception as e:
            logger.error(f"Decryption to file failed: {e}")
            raise

# Global instance
security_manager = SecurityManager()
