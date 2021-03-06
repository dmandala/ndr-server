#!/usr/bin/python3
# Copyright (C) 2017  Secured By THEM
# Original Author: Michael Casadevall <mcasadevall@them.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''Tests functionality related to traffic_reports'''

import unittest
import os
import logging
import tempfile
from datetime import datetime, timedelta

import tests.util
import ndr_server

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_CONFIG = THIS_DIR + "/test_config.yml"
TRAFFIC_REPORT_LOG = THIS_DIR + "/data/ingest/traffic_report.yml"

class TestIngests(unittest.TestCase):
    '''Tests various ingest cases'''

    def setUp(self):
        logging.getLogger().addHandler(logging.NullHandler())
        # Now load a global config object so the DB connection is open
        self._nsc = ndr_server.Config(logging.getLogger(), TEST_CONFIG)

        # We need to process test messages, so override the base directory for
        # this test
        self._db_connection = self._nsc.database.get_connection()

        # For this specific test, we need to create a few test objects
        self._test_org = ndr_server.Organization.create(
            self._nsc, "Ingest Recorders Org", db_conn=self._db_connection)
        self._test_site = ndr_server.Site.create(
            self._nsc, self._test_org, "Ingest Recorders Site", db_conn=self._db_connection)
        self._recorder = ndr_server.Recorder.create(
            self._nsc, self._test_site, "Test Recorder", "ndr_test_status",
            db_conn=self._db_connection)

        # We need a test file contact
        file_descriptor, self._test_contact = tempfile.mkstemp()
        os.close(file_descriptor) # Don't need to write anything to it

        file_descriptor, self._test_contact_zip = tempfile.mkstemp()
        os.close(file_descriptor) # Don't need to write anything to it

        file_descriptor, self._test_contact_inline = tempfile.mkstemp()
        os.close(file_descriptor) # Don't need to write anything to it


        ndr_server.Contact.create(
            self._nsc, self._test_org, "file", self._test_contact,
            db_conn=self._db_connection)

        ndr_server.Contact.create(
            self._nsc, self._test_org, "file", self._test_contact_inline, output_format="inline",
            db_conn=self._db_connection)

        ndr_server.Contact.create(
            self._nsc, self._test_org, "file", self._test_contact_zip, output_format="zip",
            db_conn=self._db_connection)

    def tearDown(self):
        self._db_connection.rollback()
        self._nsc.database.close()
        os.remove(self._test_contact)
        os.remove(self._test_contact_zip)
        os.remove(self._test_contact_inline)

    def test_geoip_reporting(self):
        '''Tests GeoIP reporting information'''
        tests.util.ingest_test_file(self, TRAFFIC_REPORT_LOG)

        report_manager = ndr_server.TsharkTrafficReportManager(self._nsc,
                                                               self._test_site,
                                                               self._db_connection)
        geoip_report = report_manager.retrieve_geoip_breakdown(
            datetime.now() - timedelta(days=1),
            datetime.now(),
            self._db_connection)

        self.assertEqual(len(geoip_report), 14)

    def test_machine_breakdown_reporting(self):
        '''Tests breaking down data by machine'''
        tests.util.ingest_test_file(self, TRAFFIC_REPORT_LOG)

        report_manager = ndr_server.TsharkTrafficReportManager(self._nsc,
                                                               self._test_site,
                                                               self._db_connection)
        local_ip_report = report_manager.retrieve_geoip_by_local_ip_breakdown(
            datetime.now() - timedelta(days=1),
            datetime.now(),
            self._db_connection)

        # Need less crappy tests
        self.assertEqual(len(local_ip_report), 15)

    def test_full_host_breakdown(self):
        '''Tests full host breakdown'''
        tests.util.ingest_test_file(self, TRAFFIC_REPORT_LOG)

        report_manager = ndr_server.TsharkTrafficReportManager(self._nsc,
                                                               self._test_site,
                                                               self._db_connection)
        full_breakdown_report = report_manager.retrieve_full_host_breakdown(
            datetime.now() - timedelta(days=1),
            datetime.now(),
            self._db_connection)

        self.assertEqual(len(full_breakdown_report), 74)

    def test_full_host_breakdown(self):
        '''Tests internet host breakdown'''
        tests.util.ingest_test_file(self, TRAFFIC_REPORT_LOG)

        report_manager = ndr_server.TsharkTrafficReportManager(self._nsc,
                                                               self._test_site,
                                                               self._db_connection)
        internet_host_breakdown = report_manager.retrieve_internet_host_breakdown(
            datetime.now() - timedelta(days=1),
            datetime.now(),
            self._db_connection)

        self.assertEqual(len(internet_host_breakdown), 74)

    def test_email_report(self):
        '''Tests generation of email reports and such'''
        tests.util.ingest_test_file(self, TRAFFIC_REPORT_LOG)

        report_manager = ndr_server.TsharkTrafficReportManager(self._nsc,
                                                               self._test_site,
                                                               self._db_connection)

        report_manager.generate_report_emails(datetime.now() - timedelta(days=1),
                                              datetime.now(),
                                              db_conn=self._db_connection,
                                              send=True)

        with open(self._test_contact_inline, 'r') as f:
            alert_email = f.read()

        self.assertIn("This is a snapshot of internet traffic broken down by destination IP", alert_email)

    def test_email_report_csv(self):
        '''Tests generation of email reports with CSV and such'''
        tests.util.ingest_test_file(self, TRAFFIC_REPORT_LOG)

        report_manager = ndr_server.TsharkTrafficReportManager(self._nsc,
                                                               self._test_site,
                                                               self._db_connection)

        report_manager.generate_report_emails(datetime.now() - timedelta(days=1),
                                              datetime.now(),
                                              db_conn=self._db_connection,
                                              send=True)

        with open(self._test_contact, 'r') as f:
            alert_email = f.read()

        self.assertIn("Attached to this email is a CSV breakdown of all traffic for the last 24 hours.", alert_email)

        with open('/tmp/zip_email.eml', 'w') as f:
            f.write(alert_email)

    def test_email_report_zip(self):
        '''Tests generation of email reports with CSV in a ZIP and such'''
        tests.util.ingest_test_file(self, TRAFFIC_REPORT_LOG)

        report_manager = ndr_server.TsharkTrafficReportManager(self._nsc,
                                                               self._test_site,
                                                               self._db_connection)

        report_manager.generate_report_emails(datetime.now() - timedelta(days=1),
                                              datetime.now(),
                                              db_conn=self._db_connection,
                                              send=True)

        with open(self._test_contact_zip, 'r') as f:
            alert_email = f.read()

        self.assertIn("Attached to this email is a CSV breakdown of all traffic for the last 24 hours.", alert_email)
