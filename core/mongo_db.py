import os
import logging
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# Try to get MONGODB_URI from environment
MONGODB_URI = os.getenv("MONGODB_URI", "")

mongo_client = None
db = None

if MONGODB_URI:
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Attempt to ping to verify connection
        mongo_client.admin.command('ping')
        db = mongo_client.get_database("psi_resume_analyser") # Set specific db name since the URI appName doesn't specify one
        logger.info("Connected to MongoDB successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        mongo_client = None
        db = None
else:
    logger.warning("MONGODB_URI not found in environment variables. Auth and memory will be disabled.")

def get_db():
    return db
