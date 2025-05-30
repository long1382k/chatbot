import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "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")
MODEL_CONFIG_PATH = "app/models.yaml"
