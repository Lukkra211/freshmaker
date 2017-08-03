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
# Written by Chenxiong Qi <cqi@redhat.com>

import json
import koji
import time

from itertools import chain

from freshmaker import conf
from freshmaker import log
from freshmaker import db
from freshmaker.events import BrewSignRPMEvent
from freshmaker.handlers import BaseHandler
from freshmaker.kojiservice import koji_service
from freshmaker.lightblue import LightBlue
from freshmaker.pulp import Pulp
from freshmaker.errata import Errata
from freshmaker.types import ArtifactType, ArtifactBuildState

from odcs.client.odcs import ODCS
from odcs.client.odcs import AuthMech


class BrewSignRPMHandler(BaseHandler):
    """Rebuild docker images when a RPM is signed in Brew"""

    name = 'BrewSignRPMHandler'

    def can_handle(self, event):
        return isinstance(event, BrewSignRPMEvent)

    def handle(self, event):
        """Rebuild docker images which contains this signed RPM

        Before rebuilding docker images, freshmaker has to find which docker
        images includes the signed RPM. As of writing this feature, this
        information is stored in LightBlue, and need to use content_sets to
        find out those images.

        There are several external services taking part in the process of
        rebuilding docker images.

        * Errata Tool: get which advisories contains the signed RPM, and Pulp
          repositories the signed RPM will end up eventually when shipped.
        * Pulp: query content set with repositories got from Errata Tool.
        * LightBlue: this is where to query docker images that contains RPMs
          from those content sets.
        """

        batches = self._find_images_to_rebuild(event)

        if not batches:
            log.info('Not find docker images to rebuild.')
            return []

        self._log_batches(batches)
        self._record_batches(batches, event)

        repo_url = self._prepare_yum_repo(event)  # noqa

        return []

    def _prepare_yum_repo(self, event):
        """Prepare a yum repo for rebuild

        Run a compose in ODCS to contain required RPMs for rebuilding images
        later.
        """
        odcs = ODCS(conf.odcs_server_url, auth_mech=AuthMech.Kerberos)
        packages = self._get_packages_for_compose(event.nvr)
        compose_source = self._get_compose_source(event.nvr)

        if compose_source is None:
            log.error('Build %s is not the latest build in its all tags.',
                      event.nvr)
            return

        log.info('Generate new compose for rebuild: '
                 'source: %s, source type: %s, packages: %s',
                 compose_source, 'tag', packages)

        new_compose = odcs.new_compose(compose_source,
                                       'tag',
                                       packages=packages)
        compose_id = new_compose['id']
        compose_url = '{0}/odcs/{1}/composes/{2}'.format(
            odcs.server_url.strip('/'), odcs.api_version, compose_id)

        log.info('Waiting for ODCS to finish the compose: %s', compose_url)

        while True:
            time.sleep(1)

            compose = odcs.get_compose(compose_id)
            state = compose['state']
            if state == 0:  # waiting for generating compose
                log.info('Waiting for generating new compose')
            elif state == 1:  # generating in progress
                log.info('ODCS is generating the compose')
            elif state == 4:  # Failed to generate compose
                log.error('ODCS fails to generate compose: %s', compose_url)
                log.error('Please consult ODCS to see what is wrong with it')
                return
            elif state == 2:  # Succeed to generate compose
                log.info('ODCS has finished to generate compose. Continue to rebuild')
                break
            else:
                log.error('Got unexpected compose state {0} from ODCS.'.format(state))
                return

        log.info('Repo URL containing packages used to rebuild container: %s',
                 new_compose['result_repo'])

        return new_compose['result_repo']

    def _get_packages_for_compose(self, nvr):
        """Get RPMs of current build NVR"""
        with koji_service(conf.koji_profile, log) as session:
            rpms = session.get_build_rpms(nvr)
        return list(set([rpm['name'] for rpm in rpms]))

    def _get_compose_source(self, nvr):
        """Get tag from which to collect packages to compose"""
        with koji_service(conf.koji_profile, log) as service:
            tag = [tag['name'] for tag in service.session.listTags(nvr)
                   if tag['name'].endswith('-candidate')][0]
            latest_build = service.session.listTagged(
                tag,
                latest=True,
                package=koji.parse_NVR(nvr)['name'])
            if latest_build and latest_build[0]['nvr'] == nvr:
                return tag

    def _log_batches(self, batches):
        """
        Logs the information about images to rebuilt using log.info(...).
        :param batches list: Output of _find_images_to_rebuild(...).
        """
        log.info('Found docker images to rebuild in following order:')
        for i, batch in enumerate(batches):
            log.info('   Batch %d (%d images):', i, len(batch))
            for image in batch:
                based_on = "based on %s" % image["parent"]["brew"]["build"] \
                    if image["parent"] else "base image"
                log.info('      - %s#%s (%s)' %
                         (image["repository"], image["commit"], based_on))

    def _record_batches(self, batches, event):
        """
        Records the images from batches to database.
        :param batches list: Output of _find_images_to_rebuild(...).
        """

        # Used as tmp dict with {brew_buil_id: ArtifactBuild, ...} mapping.
        builds = {}

        for batch in batches:
            for image in batch:
                name = image["brew"]["build"]
                parent_name = image["parent"]["brew"]["build"] \
                    if image["parent"] else None
                dep_on = builds[parent_name] if parent_name in builds else None
                build = self.record_build(
                    event, name, ArtifactType.IMAGE, 0, dep_on,
                    ArtifactBuildState.PLANNED.value)

                build_args = {}
                build_args["repository"] = image["repository"]
                build_args["commit"] = image["commit"]
                build_args["parent"] = parent_name
                build.build_args = json.dumps(build_args)
                db.session.commit()

                builds[name] = build

    def _find_images_to_rebuild(self, event):
        # When get a signed RPM, first step is to find out advisories
        # containing that RPM and has to ensure all builds are signed.
        errata = Errata(conf.errata_tool_server_url)
        advisories = errata.advisories_from_event(event)

        # Filter out advisories which are not allow by configuration
        advisories = [advisory for advisory in advisories
                      if self.allow_build(ArtifactType.IMAGE,
                                          advisory_name=advisory.name)]
        if not advisories:
            log.info("No advisories found suitable for rebuilding Docker "
                     "images")
            return []

        if not all((errata.builds_signed(advisory.errata_id)
                    for advisory in advisories)):
            log.info('Not all builds in %s are signed. Do not rebuild any '
                     'docker image until signed.', advisories)
            return []

        # Use the advisories to find out Pulp repository IDs from Errata Tool
        # and furthermore get content_sets from Pulp where signed RPM will end
        # up eventually when advisories are shipped.
        pulp_repo_ids = list(set(chain(
            *[errata.get_pulp_repository_ids(advisory.errata_id)
              for advisory in advisories]
        )))

        pulp = Pulp(server_url=conf.pulp_server_url,
                    username=conf.pulp_username,
                    password=conf.pulp_password)
        content_sets = pulp.get_content_set_by_repo_ids(pulp_repo_ids)

        log.info('RPM will end up within content sets %s', content_sets)

        # Query images from LightBlue by signed RPM's srpm name and found
        # content sets
        lb = LightBlue(server_url=conf.lightblue_server_url,
                       cert=conf.lightblue_certificate,
                       private_key=conf.lightblue_private_key)

        srpm_name = self._find_build_srpm_name(event.nvr)
        return lb.find_images_to_rebuild(srpm_name, content_sets)

    def _find_build_srpm_name(self, build_nvr):
        """Find srpm name from a build"""
        with koji_service(conf.koji_profile, log) as session:
            rpm_infos = session.get_build_rpms(build_nvr, arches='src')
            if not rpm_infos:
                raise ValueError(
                    'Build {} does not have a SRPM, although this should not '
                    'happen in practice.'.format(build_nvr))
            return rpm_infos[0]['name']