# -*- coding: utf-8 -*-
# Copyright (c) 2017  Red Hat, Inc.
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

import fedmsg.config
import mock
import freshmaker
import queue

from freshmaker import app, db, events, models, login_manager
from tests import helpers


@login_manager.user_loader
def user_loader(username):
    return models.User.find_user_by_name(username=username)


class TestViews(helpers.ModelsTestCase):
    def setUp(self):
        super(TestViews, self).setUp()
        self._init_data()
        self.client = app.test_client()

    def _init_data(self):
        event = models.Event.create(db.session, "2017-00000000-0000-0000-0000-000000000001", "RHSA-2018-101", events.TestingEvent)
        build = models.ArtifactBuild.create(db.session, event, "ed", "module", 1234)
        build.build_args = '{"key": "value"}'
        models.ArtifactBuild.create(db.session, event, "mksh", "module", 1235)
        models.ArtifactBuild.create(db.session, event, "bash", "module", 1236)
        models.Event.create(db.session, "2017-00000000-0000-0000-0000-000000000002", "RHSA-2018-102", events.TestingEvent)
        db.session.commit()
        db.session.expire_all()

    def test_monitor_api_structure(self):
        resp = self.client.get('/api/1/monitor/metrics/')
        self.assertEqual(
            len([l.startswith('# TYPE')
                 for l in resp.get_data(as_text=True).splitlines()]), 140)
        self.assertEqual(
            len([l.startswith('# HELP')
                 for l in resp.get_data(as_text=True).splitlines()]), 140)


class ConsumerTest(helpers.ModelsTestCase):
    def setUp(self):
        super(ConsumerTest, self). setUp()
        self.client = app.test_client()

    def tearDown(self):
        super(ConsumerTest, self). tearDown()

    def _create_consumer(self):
        hub = mock.MagicMock()
        hub.config = fedmsg.config.load_config()
        hub.config['freshmakerconsumer'] = True
        consumer = freshmaker.consumer.FreshmakerConsumer(hub)
        # Cleanup the queue.
        consumer.incoming = queue.Queue()
        return consumer

    def _module_state_change_msg(self, state=None):
        msg = {'body': {
            "msg_id": "2017-7afcb214-cf82-4130-92d2-22f45cf59cf7",
            "topic": "org.fedoraproject.prod.mbs.module.state.change",
            "signature": "qRZ6oXBpKD/q8BTjBNa4MREkAPxT+KzI8Oret+TSKazGq/6gk0uuprdFpkfBXLR5dd4XDoh3NQWp\nyC74VYTDVqJR7IsEaqHtrv01x1qoguU/IRWnzrkGwqXm+Es4W0QZjHisBIRRZ4ywYBG+DtWuskvy\n6/5Mc3dXaUBcm5TnT0c=\n",
            "msg": {
                "state": 5,
                "id": 70,
                "state_name": state or "ready"
            }
        }}

        return msg

    def _get_monitor_value(self, key):
        resp = self.client.get('/api/1/monitor/metrics/')
        for line in resp.get_data(as_text=True).splitlines():
            k, v = line.split(" ")[:2]
            if k == key:
                return int(float(v))
        return None

    @mock.patch("freshmaker.handlers.mbs.module_state_change.MBSModuleStateChangeHandler.handle")
    @mock.patch("freshmaker.consumer.get_global_consumer")
    def test_consumer_processing_message(self, global_consumer, handle):
        """
        Tests that consumer parses the message, forwards the event
        to proper handler and is able to get the further work from
        the handler.
        """
        consumer = self._create_consumer()
        global_consumer.return_value = consumer
        handle.return_value = [freshmaker.events.TestingEvent("ModuleBuilt handled")]

        prev_counter_value = self._get_monitor_value("messaging_received_passed_total")

        msg = self._module_state_change_msg()
        consumer.consume(msg)

        event = consumer.incoming.get()
        self.assertEqual(event.msg_id, "ModuleBuilt handled")

        counter_value = self._get_monitor_value("messaging_received_passed_total")
        self.assertEqual(prev_counter_value + 1, counter_value)