Here's a Python function to parse an NGINX access log into a `pandas` DataFrame. It assumes the **common log format** or a **combined log format**, which is typically used in NGINX:

### 🔧 Example Log Format (Combined):

```
127.0.0.1 - frank [10/Oct/2023:13:55:36 +0700] "GET /index.html HTTP/1.1" 200 1043 "http://example.com/start.html" "Mozilla/5.0"
```

---

### ✅ Python Function:

```python
import pandas as pd
import re

def parse_nginx_log(file_path):
    # Regex pattern for combined log format
    log_pattern = re.compile(
        r'(?P<ip>\S+) '                   # IP address
        r'(?P<identity>\S*) '            # Remote identity
        r'(?P<userid>\S*) '              # User ID
        r'\[(?P<time>.*?)\] '            # Timestamp
        r'"(?P<method>\S+) '             # HTTP method
        r'(?P<url>\S+) '                 # URL
        r'(?P<protocol>[^"]+)" '         # Protocol
        r'(?P<status>\d{3}) '            # Status code
        r'(?P<size>\S+) '                # Size of response
        r'"(?P<referer>[^"]*)" '         # Referer
        r'"(?P<user_agent>[^"]*)"'       # User-Agent
    )

    logs = []

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = log_pattern.match(line)
            if match:
                logs.append(match.groupdict())

    df = pd.DataFrame(logs)

    # Convert numeric fields and timestamp
    df['status'] = pd.to_numeric(df['status'], errors='coerce')
    df['size'] = pd.to_numeric(df['size'].replace('-', '0'), errors='coerce')
    df['time'] = pd.to_datetime(df['time'], format='%d/%b/%Y:%H:%M:%S %z', errors='coerce')

    return df
```

---

### 📦 Example Usage:

```python
df = parse_nginx_log("access.log")
print(df.head())
```

---

Would you like to include additional fields like response time (`$request_time`) or upstream info (`$upstream_response_time`) if present in a custom log format?


Great! Here's a **step-by-step guide** to publish your NGINX log parser as a Python package on PyPI using `pip`.

---

## ✅ Step 1: Create Project Structure

```
nginxlogparser/
├── nginxlogparser/
│   ├── __init__.py
│   └── parser.py
├── tests/
│   └── test_parser.py
├── README.md
├── LICENSE
├── pyproject.toml
```

---

## ✅ Step 2: Add Your Code

### `nginxlogparser/parser.py`

```python
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
```

### `nginxlogparser/__init__.py`

```python
from .parser import parse_nginx_log
```

---

## ✅ Step 3: Add `pyproject.toml`

### `pyproject.toml`

```toml
[project]
name = "nginxlogparser"
version = "0.1.0"
description = "A parser for NGINX access logs to Pandas DataFrames"
authors = [{ name = "Your Name", email = "your.email@example.com" }]
license = "MIT"
readme = "README.md"
requires-python = ">=3.7"
dependencies = ["pandas"]

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
```

---

## ✅ Step 4: Write a `README.md`

````markdown
# nginxlogparser

A lightweight Python parser that converts NGINX access logs into a Pandas DataFrame.

## Installation

```bash
pip install nginxlogparser
````

## Usage

```python
from nginxlogparser import parse_nginx_log

df = parse_nginx_log("access.log")
print(df.head())
```

````

---

## ✅ Step 5: Build the Package

Install required tools:

```bash
pip install build twine
````

Build the package:

```bash
python -m build
```

---

## ✅ Step 6: Upload to PyPI

First, register at [https://pypi.org/account/register/](https://pypi.org/account/register/)

Then upload:

```bash
twine upload dist/*
```

Enter your username and password when prompted.

---

## ✅ You're Done!

You can now install it via:

```bash
pip install nginxlogparser
```

---

If you’d like, I can generate a `.zip` of the structure with placeholder files for you. Want me to do that?
