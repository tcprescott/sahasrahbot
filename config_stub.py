"""
Stub config module for telemetry development.
In production, config.py is loaded from environment variables.
"""
import os

# Database
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', 'sahasrahbot')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASS = os.getenv('DB_PASS', '')

# Telemetry settings
TELEMETRY_ENABLED = os.getenv('TELEMETRY_ENABLED', 'false').lower() == 'true'
TELEMETRY_SAMPLE_RATE = float(os.getenv('TELEMETRY_SAMPLE_RATE', '1.0'))
TELEMETRY_RETENTION_DAYS = int(os.getenv('TELEMETRY_RETENTION_DAYS', '30'))
TELEMETRY_HASH_SALT = os.getenv('TELEMETRY_HASH_SALT', '')
TELEMETRY_QUEUE_SIZE = int(os.getenv('TELEMETRY_QUEUE_SIZE', '1000'))

# RaceTime
RACETIME_URL = os.getenv('RACETIME_URL', 'https://racetime.gg')

# Sentry (optional)
SENTRY_URL = os.getenv('SENTRY_URL', None)

# Debug
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
