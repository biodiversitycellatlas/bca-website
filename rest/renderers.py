from rest_framework.renderers import BaseRenderer
import csv
from io import StringIO

class CSVRenderer(BaseRenderer):
    """ Render files with comma-separated values. """
    delimiter = ','
    media_type = 'text/csv'
    format = 'csv'
    quotechar = '"'
    quoting = csv.QUOTE_MINIMAL

    def flatten(self, nested):
    	flat = {}
    	for k, v in nested.items():
    		if isinstance(v, dict):
    			for k2, v2 in v.items():
    				flat[f"{k}_{k2}"] = v2
    		else:
    			flat[k] = v
    	return flat

    def render(self, data, media_type=None, renderer_context=None):
        if not data:
            return ''

        output = StringIO()
        writer = csv.writer(output, delimiter=self.delimiter, quotechar=self.quotechar, quoting=self.quoting)

        # Handle pagination if enabled
        if isinstance(data, dict) and 'results' in data:
            total_count = data.get('count', 0)
            next_link = data.get('next', '')
            previous_link = data.get('previous', '')
            data = data['results']

            # Add comment with pagination details
            output.write(
                f"# Count: {total_count}\n"
                f"# Next: {next_link}\n"
                f"# Previous: {previous_link}\n")

        # Write headers
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                writer.writerow(self.flatten(data[0]).keys())
                for item in data:
                    writer.writerow(self.flatten(item).values())
            else:
                for item in data:
                    writer.writerow([item])
        elif isinstance(data, dict):
            writer.writerow(data.keys())
            writer.writerow(data.values())

        return output.getvalue()


class TSVRenderer(CSVRenderer):
    """ Render files with tab-separated values. """
    delimiter = '\t'
    media_type = 'text/tab-separated-values'
    format = 'tsv'
    quoting = csv.QUOTE_NONE
