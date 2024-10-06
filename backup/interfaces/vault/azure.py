import logging
import os
from typing import List

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from pydantic import BaseModel

from backup.config.models import VaultInterfaceConfig
from backup.decorators import log_execution
from backup.interfaces.interface import ClientInterfaceMixin, VaultInterface


class AzureKeyVaultInterfaceConfig(VaultInterfaceConfig):
    url: str


class AzureKeyVaultInterface(ClientInterfaceMixin, VaultInterface):
    """Concrete implementation of a vault interface for retrieving secrets
    from Azure Key Vault.

    This class provides methods for retrieving secrets from an Azure Key Vault
    instance. It connects to the vault and manages the process of retrieving
    secrets using the specified configuration settings.

    """

    config_cls = AzureKeyVaultInterfaceConfig

    def get_client(self):
        """Create a client object for the azure key vault service.

        Returns:
            azure.keyvault.secrets.SecretClient: A client object for the Azure Key Vault service.

        Raises:
            Exception: If the client object cannot be created due to invalid
                configuration settings or connectivity issues.

        """
        logger = logging.getLogger(__name__)
        logger.info("creating azure key vault client")

        credential = DefaultAzureCredential()
        client = SecretClient(
            vault_url=self.config.url,
            credential=credential,
        )

        return client

    @log_execution(
        __name__,
        prefix="loaded secrets from azure key vault",
    )
    def load(self):
        """Load secrets from the azure key vault.

        This method retrieves all secrets from the azure key vault and stores
        them in the environment for use by other components or interfaces.

        """
        logger = logging.getLogger(__name__)
        logger.info("loading secrets from azure key vault")

        for env_var_name, secret_name in self.config.secrets.items():
            os.environ[env_var_name] = self.get_secret(secret_name=secret_name)

    @log_execution(
        __name__,
        prefix="retrieved secret from azure key vault",
    )
    def get_secret(self, secret_name):
        """Retrieve a secret from the azure key vault.

        Args:
            secret_name (str): The name of the secret to retrieve from the vault.

        Returns:
            str: The value of the secret retrieved from the vault.

        Examples:
            >>> vault = AzureKeyVault(config)
            >>> secret_value = vault.get_secret("my_secret")
            >>> print(secret_value)
            "my_secret_value"

        """
        logger = logging.getLogger(__name__)
        logger.debug(
            "retrieving secret: '%s' from azure key vault: '%s'",
            secret_name,
            self.config.url,
        )

        return self.client.get_secret(secret_name).value
