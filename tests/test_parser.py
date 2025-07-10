import unittest
import pandas as pd
import tempfile
import os
from wltk.parser import log_to_dataframe

class TestLogToDataFrame(unittest.TestCase):
    def setUp(self):
        # Sample log entry in Combined format (with extra field)
        self.sample_log = (
            '127.0.0.1 - - [10/Jul/2025:09:30:00 +0700] '
            '"GET /index.html HTTP/1.1" 200 1234 '
            '"http://example.com/start" "Mozilla/5.0" "extra-info"'
        )

        # Create a temporary file and write the log to it
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        self.temp_file.write(self.sample_log + "\n")
        self.temp_file.close()

    def tearDown(self):
        # Delete the temp file after the test
        os.remove(self.temp_file.name)

    def test_log_to_dataframe(self):
        df = log_to_dataframe(self.temp_file.name)

        # Assert dataframe has one row
        self.assertEqual(len(df), 1)

        # Check the values are correctly parsed
        self.assertEqual(df.loc[0, 'hostname'], '127.0.0.1')
        self.assertEqual(df.loc[0, 'method'], 'GET')
        self.assertEqual(df.loc[0, 'url'], '/index.html')
        self.assertEqual(df.loc[0, 'status'], 200)
        self.assertEqual(df.loc[0, 'size'], 1234)
        self.assertEqual(df.loc[0, 'referer'], 'http://example.com/start')
        self.assertEqual(df.loc[0, 'user_agent'], 'Mozilla/5.0')
        self.assertEqual(df.loc[0, 'extra'], 'extra-info')
        self.assertIsInstance(df.loc[0, 'time'], pd.Timestamp)

if __name__ == '__main__':
    unittest.main()
