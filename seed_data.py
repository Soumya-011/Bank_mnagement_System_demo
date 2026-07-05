import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
from Database import connect_to_database
from Admin import hash_password

def generate_mock_data():
    connection = connect_to_database()
    if not connection:
        print("Could not connect to the database.")
        return

    # 1. Lists to generate realistic names
    first_names = ['Aarav', 'Priya', 'Vikram', 'Sneha', 'Rahul', 'Anjali', 'Rohan', 'Pooja', 'Amit', 'Neha', 'Soumya', 'Karan', 'Aditi', 'Siddharth', 'Riya']
    last_names = ['Sharma', 'Singh', 'Patel', 'Kumar', 'Das', 'Roy', 'Gupta', 'Verma', 'Pramanik', 'Joshi', 'Chopra', 'Mehta']

    accounts_data = []
    audit_data = []
    
    print("Hashing default PIN (1234) for all mock accounts. This might take a second...")
    default_pin_hash = hash_password("1234")

    # 2. Generate 60 Random Accounts
    print("Generating 60 customer accounts...")
    for _ in range(60):
        # Generate Name
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        # Generate Account Number (4 Letters + 8 Digits)
        acc_num = ''.join(random.choices(string.ascii_uppercase, k=4)) + ''.join(random.choices(string.digits, k=8))
        
        # Generate Random Balance between $500 and $25,000
        balance = round(random.uniform(500.00, 25000.00), 2)
        
        # Random account creation date within the last 90 days
        created_days_ago = random.randint(1, 90)
        created_at = datetime.now() - timedelta(days=created_days_ago)
        
        accounts_data.append((acc_num, name, default_pin_hash, balance, created_at))
        
        # Add the "Account Created" log to the audit data
        audit_data.append((acc_num, name, "Account Created", balance, created_at))

    # 3. Generate 200 Random Transactions
    print("Generating 200 random transactions...")
    actions = ['Deposit', 'Withdrawal']
    
    for _ in range(200):
        # Pick a random account from the ones we just created
        acc = random.choice(accounts_data)
        acc_num = acc[0]
        name = acc[1]
        
        action = random.choice(actions)
        amount = round(random.uniform(10.00, 2000.00), 2)
        
        # Generate a random transaction date within the last 30 days
        tx_days_ago = random.randint(0, 30)
        tx_time = datetime.now() - timedelta(days=tx_days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        audit_data.append((acc_num, name, action, amount, tx_time))

    # 4. Insert Data into PostgreSQL
    try:
        cursor = connection.cursor()
        
        # Insert Accounts
        print("Inserting accounts into the database...")
        cursor.executemany("""
            INSERT INTO accounts (account_number, account_holder_name, pin, balance, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, accounts_data)
        
        # Insert Audit Logs
        print("Inserting transactions into the audit table...")
        cursor.executemany("""
            INSERT INTO audit (account_number, account_holder_name, action, amount, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, audit_data)
        
        connection.commit()
        print("\n✅ Success! Database populated.")
        print("You can now log into any of these accounts using the PIN: 1234")
        
    except Exception as e:
        print(f"Database insertion error: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    generate_mock_data()