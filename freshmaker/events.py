# -*- coding: utf-8 -*-
# Copyright (c) 2016  Red Hat, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Written by Jan Kaluza <jkaluza@redhat.com>

import itertools

from freshmaker import conf

try:
    from inspect import signature
except ImportError:
    from funcsigs import signature


class BaseEvent(object):

    _parsers = {}

    def __init__(self, msg_id):
        """
        A base class to abstract events from different fedmsg messages.
        :param msg_id: the id of the msg (e.g. 2016-SomeGUID)
        """
        self.msg_id = msg_id

        # Moksha calls `consumer.validate` on messages that it receives, and
        # even though we have validation turned off in the config there's still
        # a step that tries to access `msg['body']`, `msg['topic']` and
        # `msg.get('topic')`.
        # These are here just so that the `validate` method won't raise an
        # exception when we push our fake messages through.
        # Note that, our fake message pushing has worked for a while... but the
        # *latest* version of fedmsg has some code that exercises the bug.  I
        # didn't hit this until I went to test in jenkins.
        self.body = {}
        self.topic = None

    @classmethod
    def register_parser(cls, parser_class):
        """
        Registers a parser for BaseEvent which is used to parse
        fedmsg in `from_fedmsg(...)` method.
        """
        BaseEvent._parsers[parser_class.name] = parser_class()

    @classmethod
    def get_parsed_topics(cls):
        """
        Returns the list of topics this class is parsing using the
        registered parsers.
        """
        topic_suffixes = []
        for parser in BaseEvent._parsers.values():
            topic_suffixes.extend(parser.topic_suffixes)
        return ['{}.{}'.format(pref.rstrip('.'), cat)
                for pref, cat
                in itertools.product(
                    conf.messaging_topic_prefix,
                    topic_suffixes)]

    def __repr__(self):
        init_sig = signature(self.__init__)

        args_strs = (
            "{}={!r}".format(name, getattr(self, name))
            if param.default != param.empty
            else repr(getattr(self, name))
            for name, param in init_sig.parameters.items())

        return "{}({})".format(type(self).__name__, ', '.join(args_strs))

    def __getitem__(self, key):
        """ Used to trick moksha into thinking we are a dict. """
        return getattr(self, key)

    def __setitem__(self, key, value):
        """ Used to trick moksha into thinking we are a dict. """
        return setattr(self, key, value)

    def get(self, key, value=None):
        """ Used to trick moksha into thinking we are a dict. """
        return getattr(self, key, value)

    def __json__(self):
        return dict(msg_id=self.msg_id, topic=self.topic, body=self.body)

    @staticmethod
    def from_fedmsg(topic, msg):
        """
        Takes a fedmsg topic and message and converts it to a BaseEvent
        object.
        :param topic: the topic of the fedmsg message
        :param msg: the message contents from the fedmsg message
        :return: an object of BaseEvent descent if the message is a type
        that the app looks for, otherwise None is returned
        """
        for parser in BaseEvent._parsers.values():
            if not parser.can_parse(topic, msg):
                continue

            return parser.parse(topic, msg)

        return None


class ModuleBuilt(BaseEvent):
    """ A class that inherits from BaseEvent to provide an event
    object for a module event generated by module-build-service
    :param msg_id: the id of the msg (e.g. 2016-SomeGUID)
    :param module_build_id: the id of the module build
    :param module_build_state: the state of the module build
    """
    def __init__(self, msg_id, module_build_id, module_build_state, name, stream):
        super(ModuleBuilt, self).__init__(msg_id)
        self.module_build_id = module_build_id
        self.module_build_state = module_build_state
        self.module_name = name
        self.module_stream = stream


class ModuleMetadataUpdated(BaseEvent):
    """
    Provides an event object for "Module metadata in dist-git updated".
    :param scm_url: SCM URL of a updated module.
    :param branch: Branch of updated module.
    """
    def __init__(self, msg_id, scm_url, branch):
        super(ModuleMetadataUpdated, self).__init__(msg_id)
        self.scm_url = scm_url
        self.branch = branch


class TestingEvent(BaseEvent):
    """
    Event useds in unit-tests.
    """
    def __init__(self, msg_id):
        super(TestingEvent, self).__init__(msg_id)


class DockerfileChanged(BaseEvent):
    """Represent the message omitted when Dockerfile is changed in a push"""

    def __init__(self, msg_id, repo_url, namespace, repo, branch, rev):
        super(DockerfileChanged, self).__init__(msg_id)
        self.repo_url = repo_url
        self.branch = branch
        self.namespace = namespace
        self.repo = repo
        self.rev = rev
