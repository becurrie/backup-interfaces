import datetime
import hashlib
import importlib
import logging
import os
import pprint
import types


def to_bool(value):
    """Convert a string to a boolean.

    This function converts a string to a boolean value. The string is
    converted to lowercase before being checked for truthy values such
    as 'true', 'yes', 'on', '1', or 't'. If the string does not match
    any of these values, the function returns False.

    Args:
        value (str): The string to convert to a boolean.

    Returns:
        bool: The boolean value of the string.

    Examples:
        >>> to_bool("true")
        True

        >>> to_bool("false")
        False

    """
    return str(value).lower() in ["true", "yes", "on", "1", "t"]


def to_upper(value):
    """Convert a string to uppercase.

    This function converts a string to uppercase using the built-in
    `str.upper()` method.

    Args:
        value (str): The string to convert to uppercase.

    Returns:
        str: The string converted to uppercase.

    Examples:
        >>> to_upper("hello, world!")
        'HELLO, WORLD!'

    """
    return value.upper()


def getenv(name, default=None, cast=None):
    """Get an environment variable with an optional default value and cast.

    This function retrieves an environment variable by name and returns its value
    as a string. If the environment variable is not found, the default value is
    returned. An optional cast parameter can be provided to convert the value to
    a specific type, such as int or bool, or any function that accepts a single
    string argument.

    Args:
        name (str): The name of the environment variable to retrieve.
        default (str): The default value to return if the environment variable is not found.
        cast (callable): An optional function to cast the value to a specific type.

    """
    value = os.getenv(name, default)

    if cast is not None:
        value = cast(value)

    return value


def get_class(cls, separator="."):
    """Get a class instance from a specified class path dynamically.

    This function will dynamically import a class from a specified class path
    and return the class object. The class path should be specified as a string,
    with the module path separated by the `separator` parameter.

    Args:
        cls (str): The class path to import.
        separator (str): The separator to use when splitting the class path.

    Returns:
        class: The class object that was imported dynamically.

    Examples:
        >>> get_class("backup.interfaces.example.BackupInterface")
        <class 'backup.interfaces.example.BackupInterface'>

        >>> get_class("backup.vaults.example.Vault")
        <class 'backup.vaults.example.Vault'>

    """
    module_path, class_name = cls.rsplit(separator, 1)

    try:
        module = importlib.import_module(module_path)
    except (ImportError, AttributeError) as exc:
        raise ImportError("unable to import module '%s'" % module_path)

    if not hasattr(module, class_name):
        raise ImportError(
            "class '%s' not found in module '%s'" % (class_name, module_path)
        )

    # getattr() is used to get the class object from the module
    # using the class name.
    return getattr(module, class_name)


def get_backup_name(base):
    """Generate a unique backup name based on a base name.

    This function generates a unique backup name by appending a
    formatted timestamp separated by an underscore to the base name.

    Args:
        base (str): The base name for the backup.

    Returns:
        str: A unique backup name based on the base name.

    Examples:
        >>> get_backup_name("backup")
        'backup_2024-10-06T09-24-10'

    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    name = "_".join([base, timestamp])

    return name


def mask_sensitive_data(data):
    """Mask sensitive data in a dictionary recursively.

    This function traverses a dictionary and masks values associated with
    keys that contain sensitive information, such as passwords, tokens,
    or secrets. The masking is performed recursively, ensuring that nested
    dictionaries and lists are also processed.

    Args:
        data (dict): The dictionary containing potentially sensitive data
                     to be masked.

    Returns:
        dict: A new dictionary with sensitive data masked, where values
              associated with sensitive keys are replaced with '********'.

    Example:
        >>> config = {
        ...     "DATABASE_PASSWORD": "mysecretpassword",
        ...     "API_TOKEN": "abcd1234efgh5678",
        ...     "USERNAME": "user1",
        ... }
        >>> masked_config = mask_sensitive_data(config)
        >>> print(masked_config)
        {
            "DATABASE_PASSWORD": "********",
            "API_TOKEN": "********",
            "USERNAME": "user1",
        }

    This function is useful for sanitizing configuration data before
    logging or displaying it, preventing sensitive information from being
    exposed.

    """
    if isinstance(data, str):
        return data

    masked = data.copy()
    sensitive = [
        "PASSWORD",
        "SECRET",
        "TOKEN",
        "KEY",
    ]

    for key, value in masked.items():
        if any(s in key.upper() for s in sensitive):
            masked[key] = "********"
        if isinstance(value, dict):
            masked[key] = mask_sensitive_data(value)
        if isinstance(value, list):
            masked[key] = [mask_sensitive_data(item) for item in value]

    return masked


def format_object(obj, mask=True):
    """Format an object into a suitable format for logging purposes.

    This function is primarily used for debugging purposes to log the
    values of various types of objects, including dictionaries, modules,
    and Pydantic models. It retrieves the relevant attributes of the
    object and masks any sensitive information before logging. It also applies
    some default

    Args:
        obj (object): The object to log. Supported object types include
            modules and Pydantic models.
        mask (bool): A flag indicating whether to mask sensitive data
            in the object before formatting. Defaults to True.

    """
    if isinstance(obj, types.ModuleType):
        obj = {
            attr: getattr(obj, attr)
            for attr in dir(obj)
            if not attr.islower()
            and not attr.startswith("__")
            and not callable(getattr(obj, attr))
        }
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump()

    if mask:
        obj = mask_sensitive_data(obj)

    return (
        "\n%s"
        % pprint.pformat(
            obj,
            indent=0,
            width=80,
        )[1:-1]
    )
