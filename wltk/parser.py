import pandas as pd
import re


class Pattrens:
    COMBINED = re.compile(
        r'(?P<hostname>\S+) '
        r'(?P<identity>\S*) '
        r'(?P<userid>\S*) '
        r'\[(?P<time>.*?)\] '
        r'"(?P<method>\S+) (?P<url>\S+) (?P<protocol>[^"]+)" '
        r'(?P<status>\d{3}) '
        r'(?P<size>\S+) '
        r'"(?P<referer>[^"]*)" '
        r'"(?P<user_agent>[^"]*)" '
        r'"(?P<extra>[^"]*)"'
    )


def log_to_dataframe(path, pattern=Pattrens.COMBINED, time_format='%d/%b/%Y:%H:%M:%S %z'):
  
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
