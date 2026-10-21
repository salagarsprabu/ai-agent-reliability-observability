import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentops.db")
CUSTOMER_API_URL = os.getenv("CUSTOMER_API_URL", "http://localhost:8001")
RISK_API_URL = os.getenv("RISK_API_URL", "http://localhost:8002")
RISK_CLIENT_TIMEOUT_SECONDS = float(os.getenv("RISK_CLIENT_TIMEOUT_SECONDS", "2"))
CUSTOMER_HASH_SALT = os.getenv("CUSTOMER_HASH_SALT", "local")
AGENT_NAME = "bank-loan-agent"
AGENT_VERSION = "0.1.0"
POLICY_V1 = "1.0.0"
POLICY_V2 = "2.0.0"
