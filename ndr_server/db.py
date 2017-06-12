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

'''NDR Server Database Helper'''

import psycopg2
import psycopg2.pool
import psycopg2.extras
import psycopg2.extensions

class Database(object):
    def __init__(self, config):
        self.config = config
        self.connection = psycopg2.pool.ThreadedConnectionPool(
            10, 100, self.config.get_pg_connect_string())

    def get_connection(self):
        '''Opens a connection for doing a transaction on'''
        connection = self.connection.getconn()
        connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
        return connection

    def return_connection(self, connection):
        '''Returns the connection to the pool'''
        self.connection.putconn(connection)

    def run_procedure_fetchone(self, proc, list_args, existing_db_conn=None):
        '''Runs a stored procedure. If an existing connection is not provided, then one
           is automatically created, and committed at the procedure. On an error, the
           transaction is automatically rolled back and the connection closed'''

        try:
            if existing_db_conn is None:
                db_conn = self.get_connection()
            else:
                db_conn = existing_db_conn

            cursor = db_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.callproc(proc, list_args)
            results = cursor.fetchone()

            if existing_db_conn is None:
                db_conn.commit()
                self.connection.putconn(db_conn)

        except psycopg2.Error:
            db_conn.rollback()
            self.connection.putconn(db_conn)
            raise

        return results

    def close(self):
        self.connection.closeall()