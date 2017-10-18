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

'''Classes relating to management of data coming from TCPDump/tshark'''

import ipaddress
import datetime
import collections
import csv
import io

from terminaltables import AsciiTable

import ndr
import ndr_server

class TsharkTrafficReport(object):
    '''Traffic logs are generated by listening programs and summarizing all packets,
    then are consolated into a traffic report entry which is stored in the database'''

    def __init__(self, config):
        self.config = config
        self.recorder = None
        self.pg_id = None
        self.traffic_log = None

    @classmethod
    def create_from_message(cls, config, recorder, log_id, message, db_conn=None):
        '''Creates traffic log entries in the database from ingest message,

           Because there's no additional metadata assoicated with traffic logs,
           the message_id is the record of a given traffic log upload'''

        ingest_log = ndr.TrafficReportMessage()
        ingest_log.from_message(message)

        traffic_log = TsharkTrafficReport(config)
        traffic_log.recorder = recorder
        traffic_log.traffic_log = ingest_log
        traffic_log.pg_id = log_id

        for traffic_entry in ingest_log.traffic_entries:
            config.database.run_procedure(
                "traffic_report.create_traffic_report",
                [log_id,
                 traffic_entry.protocol.value,
                 traffic_entry.src_address.compressed,
                 traffic_entry.src_hostname,
                 traffic_entry.src_port,
                 traffic_entry.dst_address.compressed,
                 traffic_entry.dst_hostname,
                 traffic_entry.dst_port,
                 traffic_entry.rx_bytes,
                 traffic_entry.tx_bytes,
                 traffic_entry.start_timestamp,
                 traffic_entry.duration],
                existing_db_conn=db_conn)

        return traffic_log

GeoipSummaryRecord = collections.namedtuple('GeoipSummaryRecord',
                                            'country_name region_name \
                                            total_rx_bytes total_tx_bytes')
MachineGeoIpRecord = collections.namedtuple('MachineGeoIpRecord',
                                            'local_ip country_name region_name \
                                            total_rx_bytes total_tx_bytes')
FullConnectionGeoIpRecord = collections.namedtuple('FullConnectionGeoIpRecord',
                                                   'local_ip global_ip country_name region_name \
                                                   city_name isp domain \
                                                   total_rx_bytes total_tx_bytes')
InternetHostRecord = collections.namedtuple('InternetHostRecord',
                                            'local_ip global_ip global_hostname isp')

class TsharkTrafficReportManager(object):
    '''Handles a summary of traffic report messages from the database'''

    def __init__(self, config, site, db_conn):
        self.config = config
        self.site = site
        self.organization = site.get_organization(db_conn)

    def retrieve_geoip_breakdown(self,
                                 start_period: datetime.datetime,
                                 end_period: datetime.datetime,
                                 db_conn):
        '''Breaks down all traffic by destination country'''

        geoip_results = self.config.database.run_procedure_fetchall(
            "traffic_report.report_geoip_breakdown_for_site",
            [self.site.pg_id,
             start_period,
             end_period],
            existing_db_conn=db_conn)

        geoip_records = []
        for record in geoip_results:
            geoip_records.append(
                GeoipSummaryRecord(
                    country_name=record['country_name'],
                    region_name=record['region_name'],
                    total_rx_bytes=record['total_rx_bytes'],
                    total_tx_bytes=record['total_tx_bytes']
                )
            )

        return geoip_records

    def retrieve_geoip_by_local_ip_breakdown(self,
                                             start_period: datetime.datetime,
                                             end_period: datetime.datetime,
                                             db_conn):
        '''Breaks down traffic by machine and destination'''

        local_ip_results = self.config.database.run_procedure_fetchall(
            "traffic_report.report_traffic_breakdown_in_site_by_machine",
            [self.site.pg_id,
             start_period,
             end_period],
            existing_db_conn=db_conn)

        local_ip_records = []
        for record in local_ip_results:
            local_ip_records.append(
                MachineGeoIpRecord(
                    local_ip=ipaddress.ip_address(record['local_ip']),
                    country_name=record['country_name'],
                    region_name=record['region_name'],
                    total_rx_bytes=record['total_rx_bytes'],
                    total_tx_bytes=record['total_tx_bytes']
                )
            )

        return local_ip_records

    def retrieve_internet_host_breakdown(self,
                                         start_period: datetime.datetime,
                                         end_period: datetime.datetime,
                                         db_conn):
        '''Breaks down traffic by machine and destination'''

        internet_host_results = self.config.database.run_procedure_fetchall(
            "traffic_report.report_internet_host_breakdown_for_site",
            [self.site.pg_id,
             start_period,
             end_period],
            existing_db_conn=db_conn)

        internet_host_records = []
        for record in internet_host_results:
            internet_host_records.append(
                InternetHostRecord(
                    local_ip=ipaddress.ip_address(record['local_ip']),
                    global_ip=ipaddress.ip_address(record['global_ip']),
                    global_hostname=record['global_hostname'],
                    isp=record['isp']
                )
            )

        return internet_host_records

    def retrieve_full_host_breakdown(self,
                                     start_period: datetime.datetime,
                                     end_period: datetime.datetime,
                                     db_conn):

        '''Breaks down remote traffic by machine and remote host destination'''

        traffic_breakdown_results = self.config.database.run_procedure_fetchall(
            "traffic_report.report_traffic_breakdown_for_site",
            [self.site.pg_id,
             start_period,
             end_period],
            existing_db_conn=db_conn)

        traffic_breakdown_records = []
        for record in traffic_breakdown_results:
            traffic_breakdown_records.append(
                FullConnectionGeoIpRecord(
                    local_ip=ipaddress.ip_address(record['local_ip']),
                    global_ip=ipaddress.ip_address(record['global_ip']),
                    country_name=record['country_name'],
                    region_name=record['region_name'],
                    city_name=record['city_name'],
                    isp=record['isp'],
                    domain=record['domain'],
                    total_rx_bytes=record['total_rx_bytes'],
                    total_tx_bytes=record['total_tx_bytes']
                )
            )

        return traffic_breakdown_records


    def generate_report_emails(self,
                               start_period: datetime.datetime,
                               end_period: datetime.datetime,
                               db_conn,
                               send=True,
                               csv_output=False):
        '''Generates a report email breaking down traffic by country destination'''

        tr_email = ndr_server.TsharkTrafficReportMessage(self.organization,
                                                         self.site,
                                                         self,
                                                         start_period,
                                                         end_period,
                                                         self.config,
                                                         db_conn,
                                                         csv_output)

        if send is True:
            alert_contacts = self.organization.get_contacts(db_conn=db_conn)

            # We need to get the prepped message first if we're CSV
            subject = tr_email.subject()
            message = tr_email.prepped_message()

            attachment_tuple = None
            if csv_output is True:
                current_time = datetime.datetime.today().strftime('%Y-%m-%d')
                filename = "breakdown_" + current_time + ".csv"
                attachment_tuple = [(tr_email.csv_output_text, filename)]

            for contact in alert_contacts:
                contact.send_message(
                    subject, message, attachment_tuple
                )

        return tr_email

    @staticmethod
    def generate_table_of_geoip_breakdown(traffic_report, csv_output=False):
        '''Generates a table of GeoIP breakdown'''

        # We'll sort on transmitted data
        table_data = [
            ['Country', 'Region', 'RX Bytes', 'TX Bytes', '% Rx', '% Tx']
        ]

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
            if csv_output is False:
                first_field = ""
            else:
                first_field = country

            if len(sorted_trs[country]) != 1:
                for report in sorted_trs[country]:
                    table_entry.append([
                        first_field,
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

        if csv_output is False:
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
        else:
            # This is horrible and hacky
            csv_contents = io.StringIO()
            writer = csv.writer(csv_contents)

            for row in table_data:
                writer.writerow(row)

            return csv_contents.getvalue()

    @staticmethod
    def generate_table_internet_host_traffic(traffic_report, csv_output=False):
        '''Generate internet host breakdown'''

        table_data = [
        ]

        for record in traffic_report:
            host_field = ""
            isp_field = ""
            # If we have a hostname, we'll use that, otherwise use the IP
            if record.global_hostname is not None:
                host_field = record.global_hostname
            else:
                host_field = record.global_ip

            # If we have the ISP, set it
            if record.isp is not None:
                isp_field = record.isp

            table_data.append([
                host_field,
                isp_field
            ])

        # CAST THY DUPLICATES OUT
        deduped_table_data = []
        for row in table_data:
            if row not in deduped_table_data:
                deduped_table_data.append(row)
        
        table_data = deduped_table_data

        if csv_output is False:
            table = AsciiTable(table_data)
            return table.table
        else:
            # This is horrible and hacky
            csv_contents = io.StringIO()
            writer = csv.writer(csv_contents)

            for row in table_data:
                writer.writerow(row)

            return csv_contents.getvalue()
