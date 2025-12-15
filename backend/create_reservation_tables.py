#!/usr/bin/env python3
"""
Script to create new reservation tables in the database
"""
from ocpp.db import Base, engine, Reservation, BlockedTimeSlot

print("Creating new tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")

# Verify
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Current tables: {tables}")
