#!/usr/bin/env python
"""
Database Reset Script for Pet Rent & Earn

This script will remove all data from the MongoDB database,
resetting it to a clean state. USE WITH CAUTION.

Usage:
    python reset_database.py
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import urllib.parse
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables if a .env file exists
load_dotenv()

# Get MongoDB URI from environment variable or use a default
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/petrent")

# Extract database name from URI, fallback to 'petrent' if not specified
parsed_uri = urllib.parse.urlparse(MONGODB_URI)
DB_NAME = parsed_uri.path.lstrip('/') if parsed_uri.path and parsed_uri.path != '/' else 'petrent'

async def reset_database():
    """Reset the database by removing all collections."""
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    
    # List of collections to clean
    collections = [
        "users",
        "pets",
        "conversations",
        "messages",
        "notifications",
        "notification_settings", 
        "reviews",
        "reports",
        "transactions",
        "bookings",
        "blocked_dates",
        "care_instructions",
        "health_records",
        "reminders",
        "favorites"
    ]
    
    for collection_name in collections:
        try:
            logger.info(f"Dropping collection: {collection_name}")
            await db[collection_name].delete_many({})
            logger.info(f"Collection {collection_name} has been emptied")
        except Exception as e:
            logger.error(f"Error clearing collection {collection_name}: {str(e)}")
    
    logger.info("Database reset complete!")
    client.close()

if __name__ == "__main__":
    logger.info("Starting database reset...")
    
    # Confirm with the user
    print("\n⚠️ WARNING: This will delete ALL data from your Pet Rent & Earn database!")
    print(f"Database: {DB_NAME}")
    confirm = input("\nAre you sure you want to reset the database? Type 'YES' to confirm: ")
    
    if confirm.strip().upper() == "YES":
        asyncio.run(reset_database())
        print("\n✅ Database has been reset successfully!")
    else:
        print("\n❌ Database reset cancelled.") 