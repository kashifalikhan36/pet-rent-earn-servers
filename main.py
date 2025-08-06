import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import datetime
import os

from core.config import get_settings
from routers import auth, pets, users, transactions, conversations, bookings, notifications, reviews, reports, calendar, care_instructions, health_records
# TODO: Add new router imports as they are created
# from routers import admin, payments

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

# Load application settings
settings = get_settings()

# Create upload directory if it doesn't exist
if not os.path.exists(settings.UPLOAD_DIRECTORY):
    os.makedirs(settings.UPLOAD_DIRECTORY)

# Lifespan context manager for startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.mongodb_client = AsyncIOMotorClient(settings.MONGODB_URI)
    
    # Extract database name from URI, fallback to 'petrent' if not specified
    import urllib.parse
    parsed_uri = urllib.parse.urlparse(settings.MONGODB_URI)
    db_name = parsed_uri.path.lstrip('/') if parsed_uri.path and parsed_uri.path != '/' else 'petrent'
    app.mongodb = app.mongodb_client[db_name]
    
    # Create indexes
    await create_database_indexes(app.mongodb)
    
    yield
    # Shutdown
    if hasattr(app, 'mongodb_client'):
        app.mongodb_client.close()

async def create_database_indexes(database):
    """Create necessary database indexes for better performance"""
    # User indexes
    await database.users.create_index("email", unique=True)
    await database.users.create_index("google_id", sparse=True)
    
    # Pet listing indexes
    await database.pets.create_index([("location.coordinates", "2dsphere")])
    await database.pets.create_index("owner_id")
    await database.pets.create_index("status")
    await database.pets.create_index("created_at")
    await database.pets.create_index("featured")
    
    # Transaction indexes
    await database.transactions.create_index("buyer_id")
    await database.transactions.create_index("seller_id")
    await database.transactions.create_index("pet_id")
    await database.transactions.create_index("status")
    
    # Conversation indexes
    await database.conversations.create_index("participants")
    await database.conversations.create_index("last_message_at")
    
    # Review indexes
    await database.reviews.create_index("pet_id")
    await database.reviews.create_index("reviewer_id")
    await database.reviews.create_index("reviewed_user_id")
    
    # Notification indexes
    await database.notifications.create_index("recipient_id")
    await database.notifications.create_index("is_read")
    await database.notifications.create_index("created_at")
    await database.notifications.create_index([("recipient_id", 1), ("is_read", 1)])
    
    # Notification settings index
    await database.notification_settings.create_index("user_id", unique=True)
    
    # Review indexes
    await database.reviews.create_index([("entity_id", 1), ("entity_type", 1)])
    await database.reviews.create_index("reviewer_id")
    await database.reviews.create_index("rating")
    await database.reviews.create_index("created_at")
    await database.reviews.create_index([("entity_id", 1), ("reviewer_id", 1), ("entity_type", 1)], unique=True)
    await database.reviews.create_index("transaction_id", sparse=True)
    
    # Report indexes
    await database.reports.create_index("reporter_id")
    await database.reports.create_index([("entity_id", 1), ("entity_type", 1)])
    await database.reports.create_index("status")
    await database.reports.create_index("created_at")
    await database.reports.create_index([("reporter_id", 1), ("entity_id", 1), ("entity_type", 1)])
    
    # Calendar indexes
    await database.blocked_dates.create_index("pet_id")
    await database.blocked_dates.create_index("start_date")
    await database.blocked_dates.create_index("end_date")
    await database.blocked_dates.create_index([("pet_id", 1), ("start_date", 1), ("end_date", 1)])
    await database.bookings.create_index([("start_date", 1), ("end_date", 1)])
    
    # Care instructions index
    await database.care_instructions.create_index("pet_id", unique=True)
    
    # Health records indexes
    await database.health_records.create_index("pet_id")
    await database.health_records.create_index("record_type")
    await database.health_records.create_index("date")
    await database.health_records.create_index("created_by")
    await database.health_records.create_index("reminder_date")
    
    # Reminders index
    await database.reminders.create_index("user_id")
    await database.reminders.create_index("pet_id")
    await database.reminders.create_index("reminder_date")
    await database.reminders.create_index("health_record_id", sparse=True)

# Create FastAPI app
app = FastAPI(
    title="Pet Rent & Earn API",
    description="API for pet rental and earning platform - rent pets, earn money, connect pet lovers",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIRECTORY), name="uploads")

# Include routers with API prefix
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(pets.router, prefix="/api/pets", tags=["pets"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(care_instructions.router, prefix="/api/care-instructions", tags=["care-instructions"])
app.include_router(health_records.router, prefix="/api/health-records", tags=["health-records"])

# TODO: Include new routers as they are created
# app.include_router(admin.router, prefix="/api/admin", tags=["Admin Panel"])
# app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    try:
        # Test database connection
        if hasattr(app, 'mongodb'):
            await app.mongodb.admin.command('ping')
            db_status = "connected"
        else:
            db_status = "not_initialized"
        
        return {
            "status": "ok", 
            "timestamp": datetime.datetime.utcnow(),
            "service": "Pet Rent & Earn API",
            "database": db_status,
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.datetime.utcnow(),
            "service": "Pet Rent & Earn API",
            "error": str(e)
        }

# API info endpoint
@app.get("/api", tags=["info"])
async def api_info():
    return {
        "name": "Pet Rent & Earn API",
        "version": "1.0.0",
        "description": "API for pet rental and earning platform",
        "endpoints": {
            "auth": "/api/auth",
            "pets": "/api/pets",
            "transactions": "/api/transactions",
            "chat": "/api/conversations",
            "bookings": "/api/bookings",
            "notifications": "/api/notifications",
            "reviews": "/api/reviews",
            "reports": "/api/reports",
            "calendar": "/api/calendar",
            "care-instructions": "/api/care-instructions",
            "health-records": "/api/health-records",
            "admin": "/api/admin"
        }
    }

# Add debug middleware to log request details (development only)
@app.middleware("http")
async def log_requests(request, call_next):
    logger = logging.getLogger("request_logger")

    # Log request details
    logger.debug(f"Request: {request.method} {request.url}")
    
    # Check for Authorization header specifically
    auth_header = request.headers.get("Authorization")
    if auth_header:
        logger.debug(f"Authorization header present: {auth_header[:20]}...")
    else:
        logger.debug("No Authorization header found")

    response = await call_next(request)

    # Log response status
    logger.debug(f"Response status: {response.status_code}")

    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)