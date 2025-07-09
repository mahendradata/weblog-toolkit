import pandas as pd
import re

def parse_nginx_log(file_path):
    log_pattern = re.compile(
        r'(?P<ip>\S+) '
        r'(?P<identity>\S*) '
        r'(?P<userid>\S*) '
        r'\[(?P<time>.*?)\] '
        r'"(?P<method>\S+) '
        r'(?P<url>\S+) '
        r'(?P<protocol>[^"]+)" '
        r'(?P<status>\d{3}) '
        r'(?P<size>\S+) '
        r'"(?P<referer>[^"]*)" '
        r'"(?P<user_agent>[^"]*)"'
    )

    logs = []

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = log_pattern.match(line)
            if match:
                logs.append(match.groupdict())

    df = pd.DataFrame(logs)
    df['status'] = pd.to_numeric(df['status'], errors='coerce')
    df['size'] = pd.to_numeric(df['size'].replace('-', '0'), errors='coerce')
    df['time'] = pd.to_datetime(df['time'], format='%d/%b/%Y:%H:%M:%S %z', errors='coerce')
    return df
