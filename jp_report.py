from json2html import json2html

class JpHtmlReport:
    custom_css= """
        <style>
        .json-table-container {
            margin: 20px 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #333;
        }
        .json-table {
            width: 100%;
            border-collapse: collapse;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            border-radius: 8px;
            overflow: hidden;
            background: #ffffff;
        }
        .json-table th, .json-table td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #eef2f5;
            vertical-align: top;
        }
        .json-table th {
            background-color: #f4f7f6;
            color: #4a5568;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            border-bottom: 2px solid #e2e8f0;
        }
        .json-table tbody tr:hover {
            background-color: #f8fafc;
        }
        /* stack trace */
        .json-table td:last-child {
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
            font-size: 0.85rem;
            background-color: #fafbfc;
            color: #c53030;
            white-space: pre-wrap;       
            word-break: break-all;    
            border-left: 3px solid #e53e3e;
        }
        </style>
    """

    def html_report(self, file_name, json_data: list):
        #table html
        table = f'<div class="json-table-container">{json2html.convert(json=all_data, escape=False)}</div>'

        with open(file_name, "w") as f:
            f.write(self.custom_css + table)