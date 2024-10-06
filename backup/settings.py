import os

import dotenv

from backup import utils

# load the .env file (if one is present in the application),
# production like environments might not use .env file, but rather
# set environment variables directly on the system.

dotenv.load_dotenv()

# Logging Configuration
# ---------------------

LOG_LEVEL = utils.getenv("LOG_LEVEL", default="INFO", cast=utils.to_upper)
LOG_FILE_DIR = utils.getenv("LOG_FILE_DIR", default="logs")
LOG_FILE_NAME = utils.getenv("LOG_FILE_NAME", default="backup.log")
LOG_FILE_RETENTION = utils.getenv("LOG_RETENTION", default=5, cast=int)
LOG_FILE_MAX_SIZE = utils.getenv("LOG_MAX_SIZE", default=10485760, cast=int)
LOG_FORMAT = utils.getenv(
    "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Backup Configuration
# --------------------
#
# this is the main configuration section for the backup application,
# and encapsulated more broad and higher level configurations for the
# backup process, more specific configurations are stored in the
# actual configuration yaml file that's loaded by the application.

# the path to the configuration file that the application will use
# to load the configuration values from.

BACKUP_CONFIG_PATH = utils.getenv("BACKUP_CONFIG_PATH")

# specify a chunk size that will be used by the application when moving
# files around to the storage interface specified in the configuration.
# chunked uploads will be used for all files, and depending on the network
# limitations, or memory constraints, this value can be adjusted to a
# suitable value.

BACKUP_UPLOAD_CHUNK_SIZE = utils.getenv(
    "BACKUP_UPLOAD_CHUNK_SIZE", default=4 * 1024 * 1024, cast=int
)

# specify the number of concurrent uploads that the application will
# perform when uploading files to the storage interface. this value
# can be adjusted based on the network limitations, or specs of the
# machine running the application.

BACKUP_UPLOAD_CONCURRENCY = utils.getenv(
    "BACKUP_UPLOAD_CONCURRENCY", default=20, cast=int
)


# Sentry Configuration
# --------------------

# sentry is a service that provides error tracking and monitoring for applications,
# it can be used to track errors and exceptions that occur in the application, and
# provide detailed information about the error, including the stack trace, and the
# context in which the error occurred.

SENTRY_ENABLED = utils.getenv("SENTRY_ENABLED", default=False, cast=utils.to_bool)
SENTRY_DSN = utils.getenv("SENTRY_DSN")
SENTRY_ENVIRONMENT = utils.getenv("SENTRY_ENVIRONMENT")
SENTRY_TRACES_SAMPLE_RATE = utils.getenv(
    "SENTRY_TRACES_SAMPLE_RATE", default=1.0, cast=float
)
SENTRY_PROFILES_SAMPLE_RATE = utils.getenv(
    "SENTRY_PROFILES_SAMPLE_RATE", default=1.0, cast=float
)

# if sentry is enabled, we'll initialize the sentry sdk with the
# configuration values specified in the environment.

if SENTRY_ENABLED:

    # sentry_sdk is a client library that can be used to interact with the sentry
    # service, and it provides a way to capture and send events to the sentry service,
    # we import it only if sentry is enabled by the application, otherwise we keep it out
    # of the application's dependencies.

    import sentry_sdk

    # initialize the sentry sdk with the configuration values specified in the environment.
    # this will configure the sentry sdk to send events to the sentry service, and provide
    # the necessary context for the events that are sent.

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
    )
