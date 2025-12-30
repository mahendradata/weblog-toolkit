import pandas as pd
import re


class Patterns:
    """Pre-compiled regular expressions for common Apache log formats.

    Log format references
    ---------------------
    * **Common Log Format (CLF)** - the classic seven-field log.
    * **Combined Log Format** - CLF + Referer + User-Agent (and sometimes an extra field).
    """

    # ------------------------------------------------------------------
    # Apache **Combined Log Format** regex
    # ------------------------------------------------------------------
    # Example (one long line):
    # 127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326 \
    #     "http://example.com/start.html" "Mozilla/4.08 [en] (Win98; I ;Nav)" "-"
    # ------------------------------------------------------------------
    COMBINED = re.compile(
        r'(?P<hostname>\S+) '              # Client IP or hostname
        r'(?P<identity>\S*) '              # identd, usually "-"
        r'(?P<userid>\S*) '                # Authenticated user id
        r'\[(?P<time>[^\]]+)\] '           # Timestamp
        r'"(?P<method>\S+) '               # HTTP method (GET, POST, ...)
        r'(?P<url>\S+) '                   # Requested URL
        r'(?P<protocol>[^"]+)" '           # Protocol & version
        r'(?P<status>\d{3}) '              # Status code
        r'(?P<size>\S+) '                  # Response size ("-" if zero)
        r'"(?P<referer>[^"]*)" '           # Referer header (may be "-")
        r'"(?P<user_agent>[^"]*)" '        # User-Agent string
        r'"(?P<extra>[^"]*)"'              # Optional extra field (e.g., X-Forwarded-For)
    )

    # ------------------------------------------------------------------
    # Apache **Common Log Format (CLF)** regex
    # ------------------------------------------------------------------
    # Example:
    # 127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326
    # ------------------------------------------------------------------
    COMMON = re.compile(
        r'(?P<hostname>\S+) '              # Client IP or hostname
        r'(?P<identity>\S*) '              # identd, usually "-"
        r'(?P<userid>\S*) '                # Authenticated user id
        r'\[(?P<time>[^\]]+)\] '           # Timestamp
        r'"(?P<method>\S+) '               # HTTP method
        r'(?P<url>\S+) '                   # Requested URL
        r'(?P<protocol>[^"]+)" '           # Protocol/version
        r'(?P<status>\d{3}) '              # Status code
        r'(?P<size>\S+)'                   # Response size
    )


# Example usage:
# match = Patterns.COMMON.match(log_line)
# if match:
#     print(match.groupdict())



def log_to_dataframe(path, pattern=Patterns.COMBINED, time_format='%d/%b/%Y:%H:%M:%S %z'):
  
    logs = []

    with open(path, 'r', encoding='utf-8') as file:
        for line in file:
            match = pattern.match(line)
            if match:
                logs.append(match.groupdict())

    df = pd.DataFrame(logs)
    df['status'] = pd.to_numeric(df['status'], errors='coerce')
    df['size'] = pd.to_numeric(df['size'].replace('-', '0'), errors='coerce')
    df['time'] = pd.to_datetime(df['time'], format=time_format, errors='coerce')
    return df
