# This contains the default implementations for all of mush's interfaces.
import csv
import os
from collections import OrderedDict
from mush import interfaces, engine


class data_store(interfaces.data_store):
    __keyname__ = "csv"
    __config_defaults__ = {
        'location': os.path.expanduser('~/.mush/datastore.csv')}

    def __init__(self):
        self.data_file = self.cfg("location")
        self._column_headers = list()
        self._row_data = OrderedDict()
        self._parse_csv()

    @engine.fallthrough_pipeline('access_secret')
    def environment_variables(self, alias):
        # Extract the relevant environment variables for alias
        env_vars = OrderedDict()
        column_index = self._column_headers.index(alias)
        for row_header, row in self._row_data.items():
            env_vars[row_header] = row[column_index]
        return env_vars

    def available_aliases(self):
        return self._column_headers

    def _parse_csv(self):
        csv_file = open(self.data_file, 'rb')
        csv_data = csv.reader(csv_file, delimiter=',', quotechar='"')
        self._column_headers = csv_data.next()[1:]

        # Parse data
        for row in csv_data:
            # Extract the row data
            row_header = row[0]
            row_list = row[1:]
            self._row_data[row_header] = row_list
