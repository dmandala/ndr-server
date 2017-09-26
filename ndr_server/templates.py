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

'''Contains all the templates for emails and such'''

import textwrap
import datetime
import string
import pytz
from terminaltables import AsciiTable

# pylint: disable=line-too-long

# NOTE: Each paragraph MUST be a single line as this code will automatically reflow
# to a proper size. Be mindful when editing this file!


class BaseTemplate(object):
    '''Simple message templates for doing stuff'''

    def __init__(self, organization, site, recorder, event_time):
        self.organization = organization
        self.site = site
        self.recorder = recorder
        self.event_time = event_time

        # Calculate out the event time
        if event_time is not None:
            self.time_str = datetime.datetime.fromtimestamp(
                self.event_time, pytz.timezone('America/New_York')).strftime('%Y-%m-%d %H:%M:%S%z (%Z)')
        else:
            self.time_str = "None"
        self.subject_text = "Base Template - Not Used"
        self.message = "Base Template Message - If you see this, it's a bug"
        self.footer = '''Sincerely Yours,
The Secured By THEM Team

You are recieving this message because you are a designated alert contact for $org_name. To be removed from future alert contacts, contact us to be removed from the alert list.

All messages from Secured By THEM are digitially signed with S/MIME authethication, for more information, please see please check https://securedbythem.com/genuine-message. If this watermark is missing, this message may be a forgery. If so, please contact as soon as possible.

For more information, please contact us at +1-917-716-2585 at any time day or night to review and verify recent activity detected by your Network Data Recorder. You may also contact us by replying to this email.
'''

    def replace_tokens(self, text):
        '''Replaces tokens in the template'''
        pass

    def subject(self):
        '''Returns string replaced subject line'''
        return self.replace_tokens(self.subject_text)

    def prepped_message(self):
        '''Returns a message ready to send'''
        base_msg = self.replace_tokens(self.message)

        final_text = ""
        for line in base_msg.splitlines():
            final_text += textwrap.fill(line, width=98)
            final_text += "\n"

        # Add a spacer for the signature
        final_text += "\n"

        finalized_footer = self.replace_tokens(self.footer)
        for line in finalized_footer.splitlines():
            final_text += textwrap.fill(line, width=98)
            final_text += "\n"

        return final_text


class TestAlertTemplate(BaseTemplate):
    '''Template used when alerts are sent'''
    def __init__(self, organization, site, recorder, event_time):
        BaseTemplate.__init__(self, organization, site, recorder, event_time)
        self.subject_text = "ALERT: Recorder $recorder_human_name Is Testing Alerts"
        self.message = '''The recorder $recorder_human_name at site $site_name installed for $org_name has issued a test alert message to confirm the functionality of Secured By THEM's automated alert messages. This message was generated at $time.

As part of this alert test, please verify that this message is properly signed as an authentic message by Secured By THEM. See below for more details.
'''

    def replace_tokens(self, text):
        template = string.Template(text)
        return template.substitute(
            recorder_human_name=self.recorder.human_name,
            org_name=self.organization.name,
            site_name=self.site.name,
            time=self.time_str)

class UnknownMachineTemplate(BaseTemplate):
    '''Template used for when unknown machines are detected'''
    def __init__(self, organization, site, recorder, hosts, event_time):
        BaseTemplate.__init__(self, organization, site, recorder, event_time)

        if len(hosts) == 1:
            self.subject_text = "ALERT: Unknown Machine Detected At $site_name"
        else:
            self.subject_text = "ALERT: Unknown Machines Detected At $site_name"

        self.hosts = hosts
        self.machine_info = '''
Unknown Hosts:
$host_pp'''
        self.message = '''The recorder $recorder_human_name at site $site_name installed for $org_name has following unknown machines. If you recently changed or aded a machine to your network, please contact us to add it to your network baseline.

If not, check to see if any employee has connected a phone or similar device to your network without permission.

$machine_text
This alert will repeat once every four hours until the machine is either whitelisted or removed from the network
'''


    def generate_machine_text(self):
        # Now for each machine, create a text output for that machine
        printed_hosts = ""
        for host in self.hosts:
            pp_str = host.pretty_print_str()
            for line in pp_str.splitlines():
                printed_hosts += '    ' + line + '\n'
            printed_hosts += '\n'

        machine_text = string.Template(self.machine_info)
        return machine_text.substitute(
            host_pp=printed_hosts
        )

    def replace_tokens(self, text):
        '''Does additional token replacement for unknown machines'''
        base_template = string.Template(text)
        return base_template.substitute(
            machine_text=self.generate_machine_text(),
            recorder_human_name=self.recorder.human_name,
            org_name=self.organization.name,
            site_name=self.site.name,
            time=self.time_str
        )

class RecorderAlertMessage(BaseTemplate):
    '''Template used when alerts are sent'''
    def __init__(self, organization, site, recorder, event_time, program, alert):
        BaseTemplate.__init__(self, organization, site, recorder, event_time)
        self.program = program
        self.alert = alert

        self.subject_text = "ALERT: $program On Recorder $recorder_human_name Has Raised An Alert"
        self.message = '''The recorder $recorder_human_name at site $site_name installed for $org_name has raised an alert for $program. The alert is as follows:

$alert
'''

    def replace_tokens(self, text):
        '''Does additional token replacement for unknown machines'''
        base_template = string.Template(text)
        return base_template.substitute(
            alert=self.alert,
            program=self.program,
            recorder_human_name=self.recorder.human_name,
            org_name=self.organization.name,
            site_name=self.site.name,
            time=self.time_str
        )

class SnortTrafficReportMessage(BaseTemplate):
    '''Snort Traffic Reporting Emails'''
    def __init__(self, organization, site, traffic_report):
        BaseTemplate.__init__(self, organization, site, None, None)
        self.traffic_report = traffic_report
        self.subject_text = "Daily SNORT Traffic Report For Site $site_name"
        self.message = '''This is a snapshot of internet traffic broken down by destination IP broken down by country, and regional subdivisions for the last 24 hours. GeoIP data is provided by GeoLite2 data available from MaxMind.

Traffic Breakdown By Country
===
$country_breakdown'''

    def generate_country_breakdown(self):
        '''Generates a breakdown of the traffic'''

        # We'll sort on transmitted data
        table_data = [
            ['Country', 'Subdivision', '% Transmitted', '% Received', 'TX Packets', 'RX Packets']
        ]

        tx_entry_dict = {}

        for country, values in self.traffic_report.statistics_dicts.items():
            table_entry = []

            # First add the country
            country_line = [
                country,
                "",
                values['transmit_percentage'],
                values['receive_percentage'],
                values['txpackets'],
                values['rxpackets']
            ]
            table_entry.append(country_line)

            # Now the subdivisions of each country
            for subdivision, subvalues in values['subdivisions'].items():
                sub_line = [
                    "",
                    subdivision,
                    subvalues['transmit_percentage'],
                    subvalues['receive_percentage'],
                    subvalues['txpackets'],
                    subvalues['rxpackets']
                ]
                table_entry.append(sub_line)

            # Add it to the TX dict now

            # This can happen if we get two stat dicts with the same percentage
            if values['transmit_percentage'] in tx_entry_dict:
                tx_entry_dict[values['transmit_percentage']] += table_entry
            else:
                tx_entry_dict[values['transmit_percentage']] = table_entry

        for key in sorted(tx_entry_dict.keys(), reverse=True):
            table_data += tx_entry_dict[key]

        # Add a final line with the total
        total = [
            "Total",
            "",
            float(100),
            float(100),
            self.traffic_report.total_txpackets,
            self.traffic_report.total_rxpackets
        ]
        table_data.append([])
        table_data.append(total)

        # Now generate a pretty table and return it
        table = AsciiTable(table_data)
        return table.table

    def replace_tokens(self, text):
        '''Does additional token replacement for unknown machines'''
        base_template = string.Template(text)
        return base_template.substitute(
            org_name=self.organization.name,
            site_name=self.site.name,
            country_breakdown=self.generate_country_breakdown()
        )

class TsharkTrafficReportMessage(BaseTemplate):
    '''Snort Traffic Reporting Emails'''
    def __init__(self,
                 organization,
                 site,
                 traffic_report,
                 start_period: datetime.datetime,
                 end_period: datetime.datetime,
                 db_conn):
        BaseTemplate.__init__(self, organization, site, None, None)
        self.traffic_report = traffic_report
        self.start_period = start_period
        self.end_period = end_period
        self.db_conn = db_conn
        self.subject_text = "Daily Traffic Report (v2) For Site $site_name"
        self.message = '''This is a snapshot of internet traffic broken down by destination IP broken down by country, and regional subdivisions for the last 24 hours.

Traffic Breakdown By Country
===
$country_breakdown'''

    def generate_country_breakdown(self):
        '''Generates a breakdown of the traffic'''

        # We'll sort on transmitted data
        table_data = [
            ['Country', 'Region', 'RX Bytes', 'TX Bytes', '% Rx', '% Tx']
        ]

        # Grab the general geoip summary and do some preprocessing on it
        traffic_report = self.traffic_report.retrieve_geoip_breakdown(self.start_period,
                                                                      self.end_period,
                                                                      self.db_conn)
        # Group the results together
        sorted_trs = {}
        unknown_entry = None
        total_tx = 0
        total_rx = 0

        # Sort it into country and regions
        for report in traffic_report:
            if report.country_name not in sorted_trs:
                sorted_trs[report.country_name] = []

            country_dict = sorted_trs[report.country_name]
            country_dict.append(report)
            total_tx += report.total_tx_bytes
            total_rx += report.total_rx_bytes

        tx_entry_dict = {}

        # Now generate the report
        for country in sorted_trs.keys():
            table_entry = []
            country_tx = 0
            country_rx = 0

            # Add up all the entries in the country
            for report in sorted_trs[country]:
                country_tx += report.total_tx_bytes
                country_rx += report.total_rx_bytes

            # Calculate the precents
            try:
                rx_percentage = (
                    "{0:.2f}".format((country_rx / total_rx) * 100)
                )
            except ZeroDivisionError:
                rx_percentage = "{0:.2f}".format(0)

            try:
                tx_percentage = (
                    "{0:.2f}".format((country_tx / total_tx) * 100)
                )
            except ZeroDivisionError:
                tx_percentage = "{0:.2f}".format(0)


            # If there's only one entry, merge them to one line

            region_field = ""
            if len(sorted_trs[country]) == 1:
                region_field = sorted_trs[country][0].region_name


            # Special Handling for the Unknown field
            if country == "Unknown":
                unknown_entry = [[
                    country,
                    "",
                    country_rx,
                    country_tx,
                    rx_percentage,
                    tx_percentage
                ]]
                continue

            # And now build the table
            table_entry.append([
                country,
                region_field,
                country_rx,
                country_tx,
                rx_percentage,
                tx_percentage
            ])

            # Calculate the precentage of the total
            if len(sorted_trs[country]) != 1:
                for report in sorted_trs[country]:
                    table_entry.append([
                        "",
                        report.region_name,
                        report.total_rx_bytes,
                        report.total_tx_bytes,
                        "",
                        ""
                    ])

            # This can happen if we get two stat dicts with the same percentage
            if tx_percentage in tx_entry_dict:
                tx_entry_dict[tx_percentage] += table_entry
            else:
                tx_entry_dict[tx_percentage] = table_entry

        for key in sorted(tx_entry_dict.keys(), reverse=True):
            table_data += tx_entry_dict[key]

        # Append the Unknown entry at the end if it exists
        if unknown_entry is not None:
            table_data += unknown_entry

        # And now the total
        table_data.append([])
        table_data.append([
            "Total",
            "",
            total_rx,
            total_rx,
            float(100),
            float(100)
        ])

        # Now generate a pretty table and return it
        table = AsciiTable(table_data)
        return table.table

    def replace_tokens(self, text):
        '''Does additional token replacement for unknown machines'''
        base_template = string.Template(text)
        return base_template.substitute(
            org_name=self.organization.name,
            site_name=self.site.name,
            country_breakdown=self.generate_country_breakdown()
        )
