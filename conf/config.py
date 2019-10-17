# -*- coding: utf-8 -*-

import os
import tempfile

from freshmaker.config import all_, any_  # noqa

# FIXME: workaround for this moment till confdir, dbdir (installdir etc.) are
# declared properly somewhere/somehow
confdir = os.path.abspath(os.path.dirname(__file__))
# use parent dir as dbdir else fallback to current dir
dbdir = os.path.abspath(os.path.join(confdir, '..')) if confdir.endswith('conf') \
    else confdir


class BaseConfiguration(object):
    # Make this random (used to generate session keys)
    SECRET_KEY = '74d9e9f9cd40e66fc6c4c2e9987dce48df3ce98542529fd0'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{0}'.format(os.path.join(
        dbdir, 'freshmaker.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    HOST = '0.0.0.0'
    PORT = 5001

    SERVER_NAME = 'localhost:5001'

    DEBUG = False
    # Global network-related values, in seconds
    NET_TIMEOUT = 120
    NET_RETRY_INTERVAL = 30

    SYSTEM = 'koji'

    # Available backends are: console, file, journal.
    LOG_BACKEND = 'journal'

    # Path to log file when LOG_BACKEND is set to "file".
    LOG_FILE = 'freshmaker.log'

    # Available log levels are: debug, info, warn, error.
    LOG_LEVEL = 'info'

    MESSAGING_TOPIC_PREFIX = ['org.fedoraproject.prod']

    # Parsers defined for parse specific messages
    PARSERS = [
        'freshmaker.parsers.internal:FreshmakerManualRebuildParser',
        'freshmaker.parsers.odcs:ComposeStateChangeParser',
    ]

    # List of enabled composing handlers.
    HANDLERS = [
        'freshmaker.handlers.internal:UpdateDBOnODCSComposeFail',
        'freshmaker.handlers.koji:RebuildImagesOnODCSComposeDone',
    ]

    # Base URL of git repository with source artifacts.
    GIT_BASE_URL = "git://pkgs.fedoraproject.org"

    # SSH base URL of git repository
    GIT_SSH_BASE_URL = "ssh://%s@pkgs.fedoraproject.org/"

    # GIT user for cloning and pushing repo
    GIT_USER = ""

    # Read Koji configuration from profile instead of reading them from
    # configuration file directly. For staging Koji, it is stg.
    KOJI_PROFILE = 'koji'
    KOJI_PROXYUSER = False
    KOJI_BUILD_OWNER = 'freshmaker'

    # Settings for docker image rebuild handler
    KOJI_CONTAINER_SCRATCH_BUILD = False

    SSL_ENABLED = False

    # whitelist for handlers to decide whether an artifact
    # can be built.
    #
    # In format of:
    #
    # { <handler_name> :
    #     { <artifact_type>: <rule(s)> }
    # }
    #
    # The `handler_name` is usually set to "global" to affect all
    # the handlers.
    #
    # The `rule(s)` part of a whitelist are dictionaries with key named as
    # some artifact attribute. The value can be str, bool or list of strings.
    # If it is list of strings, the rule matches if any string from the list
    # matches the artifact attribute.
    #
    # The rule(s) can be also grouped using the any_() or all_() functions:
    #
    #     - The any_(rule_1, rule_2, ...) matches when any of the rules
    #       matches.
    #     - The all_(rule_1, rule_2, ...) matches when all the rules matches.
    #
    # For more information see <http://pagure.io/freshmaker>.
    #
    # Here is an example of allowing container images to be build as soon as
    # an RHSA advisory with critical/important severity or with hightouch bug
    # moves to SHIPPED_LIVE:
    #
    # HANDLER_BUILD_WHITELIST = {
    #     "global": {
    #         "image": all_(
    #             {'advisory_name': 'RHSA-.*'
    #              'advisory_state: 'SHIPPED_LIVE'},
    #             any_(
    #                 {'has_hightouch_bugs': True},
    #                 {'severity': ['critical', 'important']}
    #             )
    #         )
    #     },
    # }

    # whitelist for handlers to decide whether an artifact
    # allowed to be built by whitelist should be build.
    #
    # The syntax is the same as for HANDLER_BUILD_WHITELIST, but any matched
    # artifact will *not* be rebuild.
    #
    # HANDLER_BUILD_BLACKLIST = {
    #     "global": {
    #         "image": all_(
    #             {'advisory_name': 'RHSA-.*'
    #              'advisory_state: 'SHIPPED_LIVE'},
    #             any_(
    #                 {'has_hightouch_bugs': True},
    #                 {'severity': ['critical', 'important']}
    #             )
    #         )
    #     },
    # }

    # ODCS configs
    # URL to ODCS to call APIs
    ODCS_SERVER_URL = 'https://odcs.localhost/'
    ODCS_VERIFY_SSL = True
    # Valid authentication method would be kerberos or openidc
    ODCS_AUTH_MECH = 'kerberos'
    # When use openidc authentcation, set the openidc token for accessing ODCS
    ODCS_OPENIDC_TOKEN = ''

    # Kerberos authentication Settings used to authenticated freshmaker itself
    # by other services

    # Whether to use keytab to acquire credential cache. keytab should be used
    # in a non-devel environment.
    KRB_AUTH_USE_KEYTAB = True
    # Principal used to acquire credential cache. When using a client keytab,
    # this value must be present in that keytab file. Otherwise, principal must
    # match the one in specified ccache file.
    KRB_AUTH_PRINCIPAL = ''
    # Path to freshmaker's client keytab file.
    KRB_AUTH_CLIENT_KEYTAB = ''
    # Path to credential cache file. This optional could be None when not using
    # a client keytab to acquire credential.
    KRB_AUTH_CCACHE_FILE = tempfile.mkstemp(
        suffix=str(os.getpid()), prefix="freshmaker_cc_")

    # Users in ADMINS are granted with admin permission.
    ADMINS = {
        'groups': [],
        'users': [],
    }

    # Select which authentication backend to work with. There are 3 choices
    # noauth: no authentication is enabled. Useful for development particularly.
    # kerberos: Kerberos authentication is enabled.
    # openidc: OpenIDC authentication is enabled.
    AUTH_BACKEND = ''

    # Used for Kerberos authentication and to query user's groups.
    # Format: ldap://hostname[:port]
    # For example: ldap://ldap.example.com/
    AUTH_LDAP_SERVER = ''

    # Group base to query groups from LDAP server.
    # Generally, it would be, for example, ou=groups,dc=example,dc=com
    AUTH_LDAP_GROUP_BASE = ''

    AUTH_OPENIDC_USERINFO_URI = 'https://id.fedoraproject.org/openidc/UserInfo'

    # OIDC base namespace
    # See also section pagure.io/odcs in
    # https://fedoraproject.org/wiki/Infrastructure/Authentication
    OIDC_BASE_NAMESPACE = 'https://pagure.io/freshmaker/'

    # Scope requested from Fedora Infra for permission of submitting request to
    # run a new compose.
    # See also: https://fedoraproject.org/wiki/Infrastructure/Authentication
    # Add additional required scope in following list
    AUTH_OPENIDC_REQUIRED_SCOPES = [
        'openid',
        'https://id.fedoraproject.org/scope/groups',
    ]

    # Select which messaging backend will be used, that could be fedmsg, amq,
    # in_memory or rhmsg.
    MESSAGING = 'fedmsg'
    MESSAGING_BACKENDS = {
        'fedmsg': {
            'SERVICE': 'freshmaker',
        },
        'rhmsg': {
            # Brokers to connect, e.g.
            # ['amqps://host:5671', 'amqps://anotherhost:5671']
            'BROKER_URLS': [],
            # Path to certificate file used to authenticate freshmaker
            'CERT_FILE': '',
            # Path to private key file used to authenticate freshmaker
            'KEY_FILE': '',
            # Path to trusted CA certificate bundle.
            'CA_CERT': '',
            'TOPIC_PREFIX': 'VirtualTopic.eng.freshmaker',
        },
        'in_memory': {
            'SERVICE': 'freshmaker',
        }
    }


class DevConfiguration(BaseConfiguration):
    DEBUG = True
    LOG_BACKEND = 'console'
    LOG_LEVEL = 'debug'

    MESSAGING_TOPIC_PREFIX = ['org.fedoraproject.dev', 'org.fedoraproject.stg']

    # Global network-related values, in seconds
    NET_TIMEOUT = 5
    NET_RETRY_INTERVAL = 1

    KOJI_CONTAINER_SCRATCH_BUILD = True

    LIGHTBLUE_VERIFY_SSL = False

    # During development, we usually don't need a client keytab to acquire
    # credential. Instead, kinit in default ccache with personal principal
    # often.
    KRB_AUTH_USE_KEYTAB = False
    KRB_AUTH_PRINCIPAL = ''  # Should be in form name@REAL
    # Use the default ccache
    KRB_AUTH_CCACHE_FILE = None

    AUTH_BACKEND = 'noauth'
    AUTH_OPENIDC_USERINFO_URI = 'https://iddev.fedorainfracloud.org/openidc/UserInfo'


class TestConfiguration(BaseConfiguration):
    LOG_BACKEND = 'console'
    LOG_LEVEL = 'debug'
    DEBUG = True

    SQLALCHEMY_DATABASE_URI = 'sqlite://'

    MESSAGING = 'in_memory'
    MESSAGING_SENDER = 'in_memory'

    # Global network-related values, in seconds
    NET_TIMEOUT = 3
    NET_RETRY_INTERVAL = 1

    KOJI_CONTAINER_SCRATCH_BUILD = True

    LIGHTBLUE_SERVER_URL = ''  # replace with real dev server url
    LIGHTBLUE_VERIFY_SSL = False

    # Disable caching for tests
    DOGPILE_CACHE_BACKEND = "dogpile.cache.null"

    AUTH_BACKEND = 'noauth'
    AUTH_LDAP_SERVER = 'ldap://ldap.example.com'
    AUTH_LDAP_GROUP_BASE = 'ou=groups,dc=example,dc=com'
    MAX_THREAD_WORKERS = 1

    HANDLER_BUILD_WHITELIST = {
        'GenerateAdvisorySignedEventOnRPMSign': {
            'image': {
                'advisory_state': 'REL_PREP|PUSH_READY|IN_PUSH|SHIPPED_LIVE',
            },
        },
        'UpdateDBOnAdvisoryChange': {
            'image': {
                'advisory_state': 'REL_PREP|PUSH_READY|IN_PUSH|SHIPPED_LIVE',
            },
        },
    }

    KRB_AUTH_CCACHE_FILE = "freshmaker_cc_$pid_$tid"
    ERRATA_TOOL_SERVER_URL = "http://localhost/"  # fake URL just for tests.
    SFM2_API_URL = "https://localhost"  # fake URL just for tests.


class ProdConfiguration(BaseConfiguration):
    pass
