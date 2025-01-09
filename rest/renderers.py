from rest_framework.renderers import BaseRenderer
import csv
from io import StringIO

class CSVRenderer(BaseRenderer):
    """
    Class for rendering files with comma-separated values.
    """
    delimiter = ','
    media_type = 'text/csv'
    format = 'csv'
    quotechar = '"'
    quoting = csv.QUOTE_MINIMAL

    def render(self, data, media_type=None, renderer_context=None):
        if not data:
            return ''

        # Handle pagination if enabled
        if isinstance(data, dict) and 'results' in data:
            data = data['results']

        output = StringIO()
        writer = csv.writer(output, delimiter=self.delimiter, quotechar=self.quotechar, quoting=self.quoting)

        # Write headers
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                writer.writerow(data[0].keys())
                for item in data:
                    writer.writerow(item.values())
            else:
                for item in data:
                    writer.writerow([item])
        elif isinstance(data, dict):
            writer.writerow(data.keys())
            writer.writerow(data.values())

        return output.getvalue()


class TSVRenderer(CSVRenderer):
    """
    Class for rendering files with tab-separated values.
    """
    delimiter = '\t'
    media_type = 'text/tab-separated-values'
    format = 'tsv'
    quoting = csv.QUOTE_NONE
