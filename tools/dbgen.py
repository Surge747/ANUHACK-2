import os
import sqlite3
import random
import json
from datetime import datetime, timedelta
from faker import Faker
from tqdm import tqdm # A progress bar library, install with 'pip install tqdm'

# --- CONFIGURATION ---
DB_FILE = "database/membership_sales.db"
NUM_MEMBERS = 10000

# Initialize Faker for generating realistic data
fake = Faker()

def create_database_schema(conn):
    """Creates the database tables with a detailed, interconnected schema."""
    cursor = conn.cursor()
    print("Creating database schema...")

    # Table for different membership levels
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS membership_tiers (
        tier_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tier_name TEXT NOT NULL UNIQUE,
        monthly_fee REAL NOT NULL,
        features TEXT NOT NULL -- Stored as a JSON array
    );
    """)

    # Table for marketing attribution
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS marketing_campaigns (
        campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_name TEXT NOT NULL UNIQUE,
        channel TEXT NOT NULL, -- e.g., 'Social Media', 'Email', 'Google Ads'
        start_date TEXT NOT NULL,
        end_date TEXT
    );
    """)

    # The main members table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone_number TEXT,
        address TEXT,
        city TEXT,
        state TEXT,
        zip_code TEXT,
        join_date TEXT NOT NULL,
        date_of_birth TEXT NOT NULL,
        membership_tier_id INTEGER,
        source_campaign_id INTEGER,
        is_active INTEGER NOT NULL, -- 1 for true, 0 for false
        FOREIGN KEY (membership_tier_id) REFERENCES membership_tiers(tier_id),
        FOREIGN KEY (source_campaign_id) REFERENCES marketing_campaigns(campaign_id)
    );
    """)

    # Products catalog
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock_quantity INTEGER
    );
    """)

    # Sales transaction table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        sale_date TEXT NOT NULL,
        total_price REAL NOT NULL,
        FOREIGN KEY (member_id) REFERENCES members(member_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)

    # Support tickets for "other data"
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS support_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        status TEXT NOT NULL, -- e.g., 'Open', 'In Progress', 'Resolved', 'Closed'
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        FOREIGN KEY (member_id) REFERENCES members(member_id)
    );
    """)

    conn.commit()
    print("Schema created successfully.")

def populate_static_tables(conn):
    """Populates tables with fixed, pre-defined data like tiers and products."""
    cursor = conn.cursor()
    print("Populating static tables (tiers, campaigns, products)...")

    # Membership Tiers
    tiers = [
        ('Bronze', 9.99, json.dumps(['Basic Content Access', 'Community Forum'])),
        ('Silver', 19.99, json.dumps(['All Bronze Features', 'Exclusive Articles', 'Monthly Webinar'])),
        ('Gold', 39.99, json.dumps(['All Silver Features', 'Direct Support', 'Early Access to Products'])),
        ('Platinum', 79.99, json.dumps(['All Gold Features', '1-on-1 Consultation', 'Annual Gift Box']))
    ]
    cursor.executemany("INSERT INTO membership_tiers (tier_name, monthly_fee, features) VALUES (?, ?, ?)", tiers)

    # Marketing Campaigns
    campaigns = [
        ('Q2 Social Media Blitz', 'Social Media', '2023-04-01', '2023-06-30'),
        ('Summer Email Blast', 'Email', '2023-07-15', '2023-08-15'),
        ('Holiday Referral Program', 'Referral', '2023-11-01', '2023-12-31'),
        ('2024 New Year Resolution', 'Google Ads', '2024-01-01', '2024-02-15')
    ]
    cursor.executemany("INSERT INTO marketing_campaigns (campaign_name, channel, start_date, end_date) VALUES (?, ?, ?, ?)", campaigns)

    # Products
    products = [
        ('Advanced Workshop Ticket', 'Event', 199.99, 100),
        ('Exclusive Branded T-Shirt', 'Merchandise', 24.99, 500),
        ('One-Hour Consultation', 'Service', 150.00, None),
        ('Premium Digital Content Pack', 'Digital', 49.99, None),
        ('Annual Conference Pass', 'Event', 499.00, 250),
        ('Branded Water Bottle', 'Merchandise', 15.50, 1000)
    ]
    cursor.executemany("INSERT INTO products (product_name, category, price, stock_quantity) VALUES (?, ?, ?, ?)", products)

    conn.commit()
    print("Static tables populated.")
    return {
        "tier_ids": [row[0] for row in cursor.execute("SELECT tier_id FROM membership_tiers")],
        "campaign_ids": [row[0] for row in cursor.execute("SELECT campaign_id FROM marketing_campaigns")],
        "products": list(cursor.execute("SELECT product_id, price FROM products"))
    }


def generate_dynamic_data(conn, static_ids):
    """Generates the main bulk of the data for members, sales, and tickets."""
    cursor = conn.cursor()
    
    # --- Generate Members ---
    print(f"Generating {NUM_MEMBERS} unique members...")
    members_to_insert = []
    # Weighted choices: More Bronze/Silver members than Platinum
    tier_weights = [0.4, 0.3, 0.2, 0.1] 
    
    for _ in tqdm(range(NUM_MEMBERS), desc="Generating Members"):
        join_date = fake.date_time_between(start_date="-5y", end_date="now")
        members_to_insert.append((
            fake.first_name(),
            fake.last_name(),
            fake.unique.email(),
            fake.phone_number(),
            fake.street_address(),
            fake.city(),
            fake.state_abbr(),
            fake.zipcode(),
            join_date.isoformat(),
            fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
            random.choices(static_ids["tier_ids"], weights=tier_weights, k=1)[0],
            random.choice(static_ids["campaign_ids"] + [None]), # Some members join organically
            random.choices([1, 0], weights=[0.9, 0.1], k=1)[0] # 90% are active
        ))
    cursor.executemany("""
        INSERT INTO members (first_name, last_name, email, phone_number, address, city, state, zip_code, 
        join_date, date_of_birth, membership_tier_id, source_campaign_id, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, members_to_insert)
    conn.commit()

    # Get all member IDs and their join dates for relational integrity
    member_data = list(cursor.execute("SELECT member_id, join_date FROM members"))

    # --- Generate Sales ---
    print("Generating sales data (approx. 15,000 records)...")
    sales_to_insert = []
    for member_id, join_date_str in tqdm(member_data, desc="Generating Sales"):
        # Each member makes between 0 and 5 purchases
        num_purchases = random.randint(0, 5)
        if num_purchases == 0:
            continue
        
        member_join_date = datetime.fromisoformat(join_date_str)

        for _ in range(num_purchases):
            product_id, price = random.choice(static_ids["products"])
            quantity = random.randint(1, 3)
            sale_date = fake.date_time_between(start_date=member_join_date, end_date="now")
            sales_to_insert.append((
                member_id,
                product_id,
                quantity,
                sale_date.isoformat(),
                round(price * quantity, 2)
            ))
    cursor.executemany("""
        INSERT INTO sales (member_id, product_id, quantity, sale_date, total_price)
        VALUES (?, ?, ?, ?, ?)
    """, sales_to_insert)
    conn.commit()

    # --- Generate Support Tickets ---
    print("Generating support ticket data (approx. 10,000 records)...")
    tickets_to_insert = []
    ticket_subjects = ['Billing Inquiry', 'Technical Issue', 'Feature Request', 'Account Access Problem', 'General Question']
    status_choices = ['Open', 'In Progress', 'Resolved', 'Closed']
    status_weights = [0.05, 0.1, 0.2, 0.65] # Most tickets are closed

    for member_id, join_date_str in tqdm(member_data, desc="Generating Tickets"):
        # Not every member creates a ticket
        if random.random() > 0.7: # Approx 70% of members will have at least one ticket
            continue
        
        member_join_date = datetime.fromisoformat(join_date_str)

        for _ in range(random.randint(1, 3)): # Between 1 and 3 tickets
            created_at = fake.date_time_between(start_date=member_join_date, end_date="now")
            status = random.choices(status_choices, weights=status_weights, k=1)[0]
            resolved_at = None
            if status in ['Resolved', 'Closed']:
                resolved_at = fake.date_time_between(start_date=created_at, end_date=created_at + timedelta(days=14)).isoformat()

            tickets_to_insert.append((
                member_id,
                random.choice(ticket_subjects),
                status,
                created_at.isoformat(),
                resolved_at
            ))
    cursor.executemany("""
        INSERT INTO support_tickets (member_id, subject, status, created_at, resolved_at)
        VALUES (?, ?, ?, ?, ?)
    """, tickets_to_insert)
    conn.commit()


def main():
    """Main function to orchestrate the database creation and population."""
    # Ensure the 'database' directory exists
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    
    # Delete old database file for a fresh start
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed existing database file: {DB_FILE}")

    try:
        conn = sqlite3.connect(DB_FILE)
        create_database_schema(conn)
        static_ids = populate_static_tables(conn)
        generate_dynamic_data(conn, static_ids)
        
        print("\n--- DATABASE GENERATION COMPLETE! ---")
        print(f"Database saved to: {DB_FILE}")
        print("You can now connect to this file with a SQL client to explore the data.")
        print("---------------------------------------")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()