from User import user_menu
from Admin import admin_menu
from Database import connect_to_database

def database_initialization():
    """Ensure the accounts and audit tables exist before the program runs."""
    connection = connect_to_database()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_number VARCHAR(50) PRIMARY KEY NOT NULL,
                account_holder_name VARCHAR(100) NOT NULL,
                pin VARCHAR(100) NOT NULL, -- Increased size for bcrypt hashes
                balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit (
                id SERIAL PRIMARY KEY,
                account_number VARCHAR(50) NOT NULL,
                account_holder_name VARCHAR(100) NOT NULL,
                action VARCHAR(100) NOT NULL,
                amount DECIMAL(15, 2) default 0.00,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                )
            """)
            connection.commit()
        except Exception as e:
            print(f"Initialization error: {e}")
        finally:
            cursor.close()
            connection.close()

def main():
    database_initialization()
    
    while True:
        print("\n" + "="*30)
        print("    WELCOME TO THE BANK    ")
        print("="*30)
        print("1. Customer Portal")
        print("2. Admin Portal")
        print("0. Exit")
        
        choice = input("Select an option: ").strip()
        
        if choice == '1':
            user_menu()
        elif choice == '2':
            admin_menu()
        elif choice == '0':
            print("Thank you for banking with us. Goodbye!")
            break
        else:
            print("Invalid input. Please enter a valid number.")

if __name__ == "__main__":
    main()