from os import path

# FIXME: workaround for this moment till confdir, dbdir (installdir etc.) are
# declared properly somewhere/somehow
confdir = path.abspath(path.dirname(__file__))
# use parent dir as dbdir else fallback to current dir
dbdir = path.abspath(path.join(confdir, '..')) if confdir.endswith('conf') \
    else confdir


class BaseConfiguration(object):
    DEBUG = False
    # Global network-related values, in seconds
    NET_TIMEOUT = 120
    NET_RETRY_INTERVAL = 30

    SYSTEM = 'koji'
    MESSAGING = 'fedmsg'  # or amq
    MESSAGING_TOPIC_PREFIX = ['org.fedoraproject.prod']
    PDC_URL = 'http://modularity.fedorainfracloud.org:8080/rest_api/v1'
    PDC_INSECURE = True
    PDC_DEVELOP = True

    # Available backends are: console, file, journal.
    LOG_BACKEND = 'journal'

    # Path to log file when LOG_BACKEND is set to "file".
    LOG_FILE = 'freshmaker.log'

    # Available log levels are: debug, info, warn, error.
    LOG_LEVEL = 'info'

    # List of enabled composing handlers.
    HANDLERS = [
        "freshmaker.handlers.mbs:MBS",  # Module Build Service
        "freshmaker.handlers.image_builder:DockerImageRebuildHandler",
    ]

    # Base URL of git repository with source artifacts.
    GIT_BASE_URL = "git://pkgs.fedoraproject.org"

    # SSH base URL of git repository
    GIT_SSH_BASE_URL = "ssh://%s@pkgs.fedoraproject.org/"

    # GIT user for cloning and pushing repo
    GIT_USER = ""

    # Base URL of Module Build Service.
    MBS_BASE_URL = "https://mbs.fedoraproject.org"

    # Authorization token to use when communicating with MBS.
    MBS_AUTH_TOKEN = ""

    # PDC API URL
    PDC_URL = 'http://pdc.fedoraproject.org/rest_api/v1'

    # Read Koji configuration from profile instead of reading them from
    # configuration file directly. For staging Koji, it is stg.
    KOJI_PROFILE = 'koji'
    KOJI_PROXYUSER = False
    KOJI_BUILD_OWNER = 'freshmaker'

    # Settings for docker image rebuild handler
    KOJI_CONTAINER_SCRATCH_BUILD = False


class DevConfiguration(BaseConfiguration):
    DEBUG = True
    LOG_BACKEND = 'console'
    LOG_LEVEL = 'debug'

    MESSAGING_TOPIC_PREFIX = ['org.fedoraproject.dev', 'org.fedoraproject.stg']

    # Global network-related values, in seconds
    NET_TIMEOUT = 5
    NET_RETRY_INTERVAL = 1

    KOJI_CONTAINER_SCRATCH_BUILD = True


class TestConfiguration(BaseConfiguration):
    LOG_BACKEND = 'console'
    LOG_LEVEL = 'debug'
    DEBUG = True
    MESSAGING = 'in_memory'
    PDC_URL = 'http://pdc.fedoraproject.org/rest_api/v1'

    # Global network-related values, in seconds
    NET_TIMEOUT = 3
    NET_RETRY_INTERVAL = 1
    MBS_AUTH_TOKEN = "testingtoken"

    KOJI_CONTAINER_SCRATCH_BUILD = True


class ProdConfiguration(BaseConfiguration):
    pass
