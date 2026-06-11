import os
import base64
import logging
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# 64KB chunks
CHUNK_SIZE = 64 * 1024

class SecurityManager:
    def __init__(self):
        # Master key must be exactly 32 bytes (base64-encoded) for AES-256.
        key_b64 = os.environ.get("INDICPDF_MASTER_KEY")

        if key_b64:
            try:
                self.key = base64.b64decode(key_b64)
            except Exception as e:
                raise RuntimeError(
                    f"INDICPDF_MASTER_KEY is not valid base64: {e}"
                ) from e
            if len(self.key) != 32:
                # Never silently pad/truncate — a wrong-length key is a
                # misconfiguration that would corrupt every encrypted file.
                raise RuntimeError(
                    f"INDICPDF_MASTER_KEY must decode to exactly 32 bytes "
                    f"(got {len(self.key)}). Generate one with: "
                    "python -c \"import os,base64;print(base64.b64encode(os.urandom(32)).decode())\""
                )
        elif os.environ.get("INDICPDF_ALLOW_EPHEMERAL_KEY") == "1":
            # Opt-in single-process/dev/test mode only. A random per-process
            # key means a separate worker process CANNOT decrypt these files.
            logger.warning(
                "INDICPDF_MASTER_KEY not set; using an ephemeral key "
                "(INDICPDF_ALLOW_EPHEMERAL_KEY=1). Cross-process decryption "
                "WILL fail and files are unreadable after restart. Dev only."
            )
            self.key = os.urandom(32)
        else:
            # Fail fast: a random fallback silently breaks the web↔worker
            # pipeline (separate processes get different keys → InvalidTag).
            raise RuntimeError(
                "INDICPDF_MASTER_KEY is not set. Set a base64-encoded 32-byte "
                "key (shared by the API and worker processes), or set "
                "INDICPDF_ALLOW_EPHEMERAL_KEY=1 for single-process dev/test."
            )

        self.aesgcm = AESGCM(self.key)

    def encrypt_file(self, plaintext_path: Path, ciphertext_path: Path):
        """Encrypt a file from disk using chunked AES-GCM to minimize memory footprint."""
        try:
            with open(plaintext_path, "rb") as f_in, open(ciphertext_path, "wb") as f_out:
                while True:
                    data = f_in.read(CHUNK_SIZE)
                    if not data:
                        break
                    
                    nonce = os.urandom(12)
                    # AESGCM.encrypt returns ciphertext + tag
                    encrypted_chunk = self.aesgcm.encrypt(nonce, data, None)
                    
                    # Write nonce + (ciphertext + tag)
                    f_out.write(nonce)
                    f_out.write(encrypted_chunk)
        except Exception as e:
            logger.error(f"Chunked encryption failed: {e}")
            if ciphertext_path.exists():
                ciphertext_path.unlink()
            raise

    def decrypt_to_memory(self, ciphertext_path: Path) -> bytes:
        """Decrypt a chunked file back into a single byte string (use with caution for large files)."""
        try:
            decrypted_data = []
            chunk_overhead = 12 + 16 # Nonce + Tag
            
            with open(ciphertext_path, "rb") as f_in:
                while True:
                    nonce = f_in.read(12)
                    if not nonce:
                        break
                    
                    encrypted_chunk = f_in.read(CHUNK_SIZE + 16)
                    if not encrypted_chunk:
                        break
                        
                    decrypted_chunk = self.aesgcm.decrypt(nonce, encrypted_chunk, None)
                    decrypted_data.append(decrypted_chunk)
            
            return b"".join(decrypted_data)
        except Exception as e:
            logger.error(f"Decryption to memory failed: {e}")
            raise

    def decrypt_to_file(self, ciphertext_path: Path, output_path: Path):
        """Decrypt a chunked file back to disk without loading it fully into memory."""
        try:
            with open(ciphertext_path, "rb") as f_in, open(output_path, "wb") as f_out:
                while True:
                    nonce = f_in.read(12)
                    if not nonce:
                        break
                    
                    encrypted_chunk = f_in.read(CHUNK_SIZE + 16)
                    if not encrypted_chunk:
                        break
                        
                    decrypted_chunk = self.aesgcm.decrypt(nonce, encrypted_chunk, None)
                    f_out.write(decrypted_chunk)
        except Exception as e:
            logger.error(f"Chunked decryption to file failed: {e}")
            if output_path.exists():
                output_path.unlink()
            raise

# Global instance
security_manager = SecurityManager()
