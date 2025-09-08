#!/usr/bin/env python3
"""
Seed script to populate the loads table with sample data.
"""
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.db import SessionLocal, engine
from api.models import Load, Base

def seed_loads():
    """Load sample data from JSON file into the database."""
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Load seed data
    seed_file = Path(__file__).parent / "loads_seed.json"
    
    if not seed_file.exists():
        print(f"Error: Seed file not found at {seed_file}")
        return False
    
    with open(seed_file, 'r') as f:
        loads_data = json.load(f)
    
    db = SessionLocal()
    
    try:
        # Clear existing loads
        db.query(Load).delete()
        print("Cleared existing loads...")
        
        # Insert new loads
        for load_data in loads_data:
            # Convert date strings to datetime objects
            load_data['pickup_date'] = datetime.fromisoformat(load_data['pickup_date'].replace('Z', '+00:00'))
            load_data['delivery_date'] = datetime.fromisoformat(load_data['delivery_date'].replace('Z', '+00:00'))
            
            load = Load(**load_data)
            db.add(load)
        
        db.commit()
        print(f"Successfully seeded {len(loads_data)} loads into the database.")
        
        # Verify the data
        count = db.query(Load).count()
        print(f"Total loads in database: {count}")
        
        return True
        
    except Exception as e:
        print(f"Error seeding loads: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting loads seeding...")
    success = seed_loads()
    if success:
        print("✅ Loads seeding completed successfully!")
    else:
        print("❌ Loads seeding failed!")
        sys.exit(1)
