from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, conint


class BaseModelExtra(BaseModel):
    model_config = ConfigDict(extra="allow")


class RetentionConfig(BaseModel):
    count: PositiveInt


class DirectoryConfig(BaseModel):
    src: str
    dest: str
    name: str
    exclude: Optional[List[str]] = []
    retention: Optional[RetentionConfig] = None


class BaseInterfaceConfig(BaseModelExtra):
    interface: str


class BackupInterfaceConfig(BaseInterfaceConfig):
    enabled: bool = False


class VaultInterfaceConfig(BaseInterfaceConfig):
    secrets: dict = {}


class StorageInterfaceConfig(BaseInterfaceConfig):
    pass


class Config(BaseModel):
    name: str
    enabled: bool = False
    storage: StorageInterfaceConfig
    interfaces: List[BackupInterfaceConfig] = []
    vaults: Optional[List[VaultInterfaceConfig]] = []
