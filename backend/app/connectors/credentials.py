import abc
import base64
import hashlib
import uuid
from typing import Optional, Dict
from cryptography.fernet import Fernet
from app.config import settings


class CredentialStore(abc.ABC):
    """Abstract credential store for securely isolating financial provider secrets and tokens."""

    @abc.abstractmethod
    def store_secret(
        self, user_id: uuid.UUID, connection_id: uuid.UUID, key: str, secret: str
    ) -> None:
        """Encrypts and securely stores a provider secret (e.g. API access token)."""
        pass

    @abc.abstractmethod
    def get_secret(
        self, user_id: uuid.UUID, connection_id: uuid.UUID, key: str
    ) -> Optional[str]:
        """Retrieves and decrypts a provider secret."""
        pass

    @abc.abstractmethod
    def delete_secret(
        self, user_id: uuid.UUID, connection_id: uuid.UUID, key: str
    ) -> bool:
        """Deletes a specific secret."""
        pass

    @abc.abstractmethod
    def delete_all_secrets(
        self, user_id: uuid.UUID, connection_id: uuid.UUID
    ) -> int:
        """Deletes all secrets associated with a connection (used upon disconnect)."""
        pass


class FernetCredentialStore(CredentialStore):
    """
    Secure symmetric-key credential store using Fernet (AES-128-CBC + HMAC-SHA256).
    Designed to prevent storing raw plaintext credentials in databases.
    Can be seamlessly replaced by Vault or AWS Secrets Manager in enterprise environments.
    """

    def __init__(self, master_key: Optional[str] = None):
        # Derive a 32-byte URL-safe base64 key from master key or settings.JWT_SECRET
        raw_key = master_key or settings.JWT_SECRET
        derived_bytes = hashlib.sha256(raw_key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(derived_bytes))
        # Isolated in-memory encrypted storage: (user_id_str, connection_id_str, key) -> encrypted_bytes
        self._storage: Dict[str, bytes] = {}

    def _make_key(self, user_id: uuid.UUID, connection_id: uuid.UUID, key: str) -> str:
        return f"{str(user_id)}:{str(connection_id)}:{key}"

    def store_secret(
        self, user_id: uuid.UUID, connection_id: uuid.UUID, key: str, secret: str
    ) -> None:
        if not secret:
            return
        storage_key = self._make_key(user_id, connection_id, key)
        encrypted = self._fernet.encrypt(secret.encode("utf-8"))
        self._storage[storage_key] = encrypted

    def get_secret(
        self, user_id: uuid.UUID, connection_id: uuid.UUID, key: str
    ) -> Optional[str]:
        storage_key = self._make_key(user_id, connection_id, key)
        encrypted = self._storage.get(storage_key)
        if not encrypted:
            return None
        try:
            decrypted = self._fernet.decrypt(encrypted)
            return decrypted.decode("utf-8")
        except Exception:
            return None

    def delete_secret(
        self, user_id: uuid.UUID, connection_id: uuid.UUID, key: str
    ) -> bool:
        storage_key = self._make_key(user_id, connection_id, key)
        return self._storage.pop(storage_key, None) is not None

    def delete_all_secrets(
        self, user_id: uuid.UUID, connection_id: uuid.UUID
    ) -> int:
        prefix = f"{str(user_id)}:{str(connection_id)}:"
        keys_to_delete = [k for k in self._storage.keys() if k.startswith(prefix)]
        for k in keys_to_delete:
            self._storage.pop(k, None)
        return len(keys_to_delete)


# Global default credential store instance
credential_store: CredentialStore = FernetCredentialStore()
