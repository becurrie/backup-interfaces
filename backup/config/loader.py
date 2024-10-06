import logging
import os
import re
from string import Template

import yaml
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from pydantic_core import ValidationError

from backup.config.models import Config, VaultInterfaceConfig
from backup.utils import format_object, get_class

# track the substitution marker for environment variables
# using a regular expression pattern.

RE_SUBSTITUTION = re.compile(r"\${(\w+)}")


def load_config(path):
    """Load a configuration file from a given path.

    The configuration file is expected to be in YAML format, and some additional
    validation is performed using the pydantic library to ensure the configuration
    file is valid and can be used by the application.

    Args:
        path (str): The path to the configuration file.

    Returns:
        Config: The configuration object.

    Raises:
        ValueError: If the configuration file path is not set.
        FileNotFoundError: If the configuration file is not found at the specified path.

    Examples:
        >>> load_config("config.yaml")
        Config(name='example', enabled=True, ...)

        >>> load_config("/path/to/config.yaml")
        Config(name='example', enabled=True, ...)

    """
    logger = logging.getLogger(__name__)
    logger.info("loading backup configuration from: '%s'", path)

    if path is None:
        raise ValueError(
            "configuration file path not set, please ensure the 'BACKUP_CONFIG_PATH' "
            "environment variable is set to a valid configuration file path."
        )
    if not os.path.exists(path):
        raise FileNotFoundError(
            "configuration file not found at path: '%s'" % path,
        )

    # load the configuration file from the specified path, at this point, the
    # configuration file is expected to be a valid YAML file, and the `config`
    # variable will contain the configuration data as a raw dictionary.

    config = load_yaml(path)

    # handle vault loading (if enabled) by loading the vault configuration objects
    # from the configuration file and setting the corresponding environment variables
    # with the secrets retrieved from the vaults.

    load_vault(config)

    # finally, handle environment variable substitution in the configuration file
    # by replacing any placeholders with their corresponding values from the environment
    # before returning and validating the final configuration object.

    config = sub_yaml(config)
    config = Config(**config)

    logger.debug("configuration loaded: %s" % format_object(config))

    return config


def load_vault(config):
    """Load vault configuration objects from a YAML configuration, if present,
    and set environment variables with the secrets retrieved.

    This function processes a dictionary representation of a vault configuration
    and creates the corresponding vault interface objects to retrieve the secrets.

    Those secrets are then set as environment variables to be used by the application
    during runtime.

    Args:
        config (dict):
            A dictionary containing the configuration data loaded
            from a YAML file. The dictionary may include nested
            structures (dictionaries or lists) that contain vault
            configurations.

    """
    logger = logging.getLogger(__name__)

    for vault in config.get("vaults", []):

        # we don't need to mask secrets when loading our vault,
        # since our vault should only store secret names, not the
        # actual secrets themselves. we'll log the vault configuration
        # fully, without masking any sensitive data.

        logger.info(
            "vault configuration found, loading vault: %s"
            % format_object(vault, mask=False)
        )

        # retrieve the vault interface class dynamically
        # and attempt to initialize it with the configuration
        # settings provided in the configuration file.

        vault_cls = get_class(vault["interface"])
        vault_instance = vault_cls(vault)

        for env_var_name, secret_name in vault_instance.config.secrets.items():
            os.environ[env_var_name] = vault_instance.get_secret(secret_name)


def load_yaml(path):
    """Load a YAML configuration file.

    This function reads a YAML file from the specified path and
    deserializes its contents into a Python dictionary. It uses
    the `yaml.safe_load` method to ensure that the file is
    processed securely, preventing the execution of arbitrary code.

    Args:
        path (str):
            The file system path to the YAML configuration file
            to be loaded. The function expects a valid file path
            that points to an existing YAML file.

    Returns:
        dict:
            A dictionary representing the contents of the YAML
            file. The keys in the dictionary correspond to the
            top-level keys in the YAML structure.

    Raises:
        FileNotFoundError:
            If the specified file does not exist.

        yaml.YAMLError:
            If the file cannot be parsed as valid YAML.

    Example:
        >>> config = load_yaml("config/config.yaml")
        >>> print(config)
        {
            "database": {
                "host": "localhost",
                "port": 5432,
                "user": "admin",
                "password": "secret"
            },
        }

    In this example, the `load_yaml` function reads a YAML
    configuration file located at 'config/config.yaml' and
    returns its contents as a python dictionary.

    """
    logger = logging.getLogger(__name__)
    logger.debug("loading yaml from file: %s", path)

    with open(path, "r") as file:
        data = yaml.safe_load(file)

    return data


def sub_yaml(config):
    """Load a YAML configuration file with environment variable templating.

    This function processes a dictionary representation of a YAML configuration
    file and recursively replaces any string values that contain environment
    variable placeholders with their corresponding environment variable values.
    This allows for dynamic configuration based on the current environment.

    Args:
        config (dict):
            A dictionary containing the configuration data loaded
            from a YAML file. The dictionary may include nested
            structures (dictionaries or lists) that contain string
            values which may be templated with environment variables.

    Returns:
        dict:
            A new dictionary with environment variables substituted
            for their placeholders in the original configuration.
            The structure of the returned dictionary remains the same
            as the input dictionary.

    Example:
        >>> config = {
        ...     'database': {
        ...         'host': 'localhost',
        ...         'port': '${DB_PORT}',
        ...         'user': '${DB_USER}',
        ...         'password': '${DB_PASSWORD}'
        ...     },
        ... }
        >>> os.environ['DB_PORT'] = '5432'
        >>> os.environ['DB_USER'] = 'admin'
        >>> os.environ['DB_PASSWORD'] = 'secret'
        >>> loaded_config = sub_yaml(config)
        >>> print(loaded_config)
        {
            'database': {
                'host': 'localhost',
                'port': '5432',
                'user': 'admin',
                'password': 'secret'
            },
            'logging': {
                'level': 'INFO',
                'file': 'app.log'
            }
        }

    In this example, the `load_yaml_env` function processes the given
    configuration dictionary, replacing any placeholders for environment
    variables with their actual values from the operating system.

    """

    def process(data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = sub_env_vars(value)
                else:
                    process(value)
        elif isinstance(data, list):
            for i, value in enumerate(data):
                process(value)
        return data

    return process(config)


def sub_env_vars(value):
    """Substitute environment variables in a string with their values.

    This function scans the input string for placeholders that reference
    environment variables and replaces them with the corresponding values
    from the operating system environment. If an environment variable
    is referenced but not set, a warning is logged.

    Args:
        value (str):
            The input string containing placeholders for environment
            variables in the format '${VAR_NAME}'. The function will
            replace these placeholders with the actual values of the
            environment variables.

    Returns:
        str:
            The modified string with environment variable placeholders
            replaced by their actual values. If a referenced environment
            variable is not found, its placeholder will be replaced with
            `None`, and a warning will be logged.

    Example:
        >>> os.environ['API_KEY'] = '12345'
        >>> os.environ['DATABASE_URL'] = 'postgres://user:pass@localhost/db'
        >>> config_value = "API Key: ${API_KEY}, Database URL: ${DATABASE_URL}"
        >>> updated_value = sub_env_vars(config_value)
        >>> print(updated_value)
        "API Key: 12345, Database URL: postgres://user:pass@localhost/db"

    In this example, the `sub_env_vars` function replaces the
    `${API_KEY}` and `${DATABASE_URL}` placeholders with their
    corresponding values from the environment. If any variable
    were missing, a warning would be logged, and its placeholder
    would be replaced with `None`.

    """
    logger = logging.getLogger(__name__)

    def replace(match):
        env_var = match.group(1)
        env_val = os.getenv(env_var, None)

        if env_val is None:
            logger.warning(
                "configuration contains reference to environment variable '%s' "
                "which is not set in the environment.",
                env_var,
            )

        return env_val

    return RE_SUBSTITUTION.sub(replace, value)
