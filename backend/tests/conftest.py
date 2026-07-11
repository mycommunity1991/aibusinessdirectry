import os

# Set default environment variables for testing before any imports occur
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/test_db"
os.environ["SECRET_KEY"] = "test_secret_key_that_is_long_enough"
os.environ["ENVIRONMENT"] = "testing"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:8000"
