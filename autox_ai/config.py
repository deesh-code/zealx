# config.py - Stores API keys & settings for AutoX AI

# API Account Configuration
AUTOX_AI_ACCOUNTS = [
    {"api_key": "API_KEY_1", "account_id": "ACCOUNT_ID_1"},
    {"api_key": "API_KEY_2", "account_id": "ACCOUNT_ID_2"},
    {"api_key": "API_KEY_3", "account_id": "ACCOUNT_ID_3"},
    # Add more accounts here for better reliability
]

# API Configuration
API_BASE_URL = "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/"
RETRY_LIMIT = 3  # Number of retries before failing

# Rate Limiting Configuration
RATE_LIMIT_COOLDOWN = 15  # Minutes to wait after detecting rate limit
REQUEST_TIMEOUT = 30  # Seconds to wait before timing out a request

# Daily Usage Limits (Cloudflare Worker AI)
DAILY_API_CALL_LIMIT = 100000  # Maximum API calls per day per account
DAILY_NEURON_COMPUTE_LIMIT = 10000  # Maximum neuron computations per day per account
USAGE_WARNING_THRESHOLD = 0.8  # Warn when 80% of daily limit is reached

# Performance Optimization
BACKOFF_BASE = 0.1  # Base time for exponential backoff
