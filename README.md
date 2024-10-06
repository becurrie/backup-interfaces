
# Backup Interfaces

A simple backup application that uses an interface-based approach to perform backups against your resources
using simple, and straight-forward configuration files to define and manage your backup processes.





## Table of Contents
- [Project Overview](#project-overview)
- [Features](#features)
- [Requirements](#requirements)
- [Setup and Installation](#setup-and-installation)
- [Running the Application](#running-the-application)
- [Configuration Files](#configuration-files)

## Project Overview

The **Backup Interfaces App** is designed to run scheduled backup processes against your resources using
a configuration file based approach that focuses on the ability to change or modify your backup policy without
having to change the underlying code.

The application uses an interface-based approach to define backup processes, allowing you to define and manage
your backup processes and policy in a simple and straight-forward configuration file.

## Features
- **Granular Configuration**: Define backup processes and policies using a various configuration methods.
- **Environment Configuration**: Easy to set up and manage configurations via `.env` files.
- **Secrets Management**: Implement a vaulting service in your configurations to manage secrets and sensitive data.
- **Interface-based Backups**: Define backup processes using interfaces that can be easily extended or modified to suit your needs.

## Requirements

- Python 3.9+

## Setup and Installation

If you're looking to just use the backup-interfaces app in your project, you can install it via pip:

```bash
>>> pip install backup-interfaces
```

If you're looking to contribute to the project or run the app locally, 
you can follow the steps below:

### 1. Clone the Repository

```bash
>>> git clone git@github.com:becurrie/backup-interfaces.git
```

### 2. Install Dependencies

```bash
>>> pip install -r requirements.txt
```

## Running the Application

To run the app locally, from the command line:

```bash
python backup/app.py
```

## Configuration Files

The app uses a configuration file to define and manage your backup processes. The configuration file is a simple
YAML file that defines the backup processes and policies for your resources.

Here's an example of a simple configuration file:

```yaml

name: my-backup-configuration
enabled: true

# you can define multiple vaults to manage your secrets,
# and use them in your backup configuration, e.g. to store
# your database credentials, etc.

vaults:
  - interface: interfaces.vault.azure.AzureKeyVaultInterface
    secrets:
      MY_ENV_VAR: my-secret-name
    url: https://my-key-vault.vault.azure.net/


# you can define the storage interface you will be using when the
# backup application runs, this determine where the backup files
# will be stored.

storage:
  interface: interfaces.storage.local.LocalStorageInterface
  storage_account: my-storage-account
  storage_container: my-storage-container
  storage_key: ${MY_ENV_VAR}

# you can define the backup interfaces you will be using to back up
# your resources, this determines how the backup will be performed,
# the interface used determines what configurations options are required.

interfaces:
  - interface: interfaces.backup.filesystem.FileSystemBackupInterface
    enabled: true
    directories:
      - src: /path/to/source
        dest: backups
        name: source
        retention:
          count: 5

```
