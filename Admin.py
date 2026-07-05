import bcrypt
import getpass
from Database import connect_to_database

# ==========================================
# SECURE PASSWORD HASHING SETUP
# ==========================================

def hash_password(password):
    """Generates a secure hash with a unique salt using bcrypt."""
    salt = bcrypt.gensalt()
    # bcrypt requires bytes, so we encode the password, then decode the hash to store as a string
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(input_password, stored_hashed_password):
    """Verifies a plaintext password against the stored bcrypt hash."""
    return bcrypt.checkpw(input_password.encode('utf-8'), stored_hashed_password.encode('utf-8'))

# Run this ONCE manually to set up your admin table and first admin
def setup_first_admin():
    connection = connect_to_database()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                username VARCHAR(50) PRIMARY KEY,
                password_hash VARCHAR(100) NOT NULL
            )
            """)
            
            # Create a default admin if none exists
            cursor.execute("SELECT * FROM admins WHERE username = 'admin'")
            if not cursor.fetchone():
                default_hash = hash_password("admin123") # Change this password later!
                cursor.execute("INSERT INTO admins (username, password_hash) VALUES (%s, %s)", ('admin', default_hash))
                print("Default admin created. Username: admin | Password: admin123")
            
            connection.commit()
        except Exception as e:
            print(f"Admin setup error: {e}")
        finally:
            cursor.close()
            connection.close()

# ==========================================
# AUDIT CLASS
# ==========================================
class Audit:
    def __init__(self, account_number, account_holder_name, action, amount=0.00, timestamp=None):
        self.__account_number = account_number
        self.__account_holder_name = account_holder_name
        self.__action = action
        self.__amount = amount
        self.__timestamp = timestamp

    # Fixed: Added getter methods so we don't use private mangling (e.g., _Audit__action)
    def get_action(self): return self.__action
    def get_amount(self): return self.__amount
    def get_timestamp(self): return self.__timestamp
    def get_account_number(self): return self.__account_number

    @staticmethod
    def save_to_database(account_number, account_holder_name, action, amount=0.00):
        connection = connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                insert_query = """
                INSERT INTO audit (account_number, account_holder_name, action, amount)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (account_number, account_holder_name, action, amount))
                connection.commit()
            except Exception as e:
                print(f"Audit log error: {e}")
            finally:
                cursor.close()
                connection.close()

    @classmethod
    def load_specific_audit_logs(cls, account_number):
        connection = connect_to_database()
        audit_logs = []
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("""
                SELECT account_number, account_holder_name, action, amount, timestamp 
                FROM audit 
                WHERE account_number = %s 
                ORDER BY timestamp DESC
                """, (account_number,))
                results = cursor.fetchall()
                for row in results:
                    audit_logs.append(cls(row[0], row[1], row[2], row[3], row[4]))
            except Exception as e:
                print(f"Error loading specific logs: {e}")
            finally:
                cursor.close()
                connection.close()
        return audit_logs
    
    @classmethod
    def create_new_admin(cls, username, password):
        connection = connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                hashed_password = hash_password(password)
                cursor.execute("INSERT INTO admins (username, password_hash) VALUES (%s, %s)", (username, hashed_password))
                connection.commit()
                print(f"Admin '{username}' created successfully.")
            except Exception as e:
                print(f"Error creating admin: {e}")
            finally:
                cursor.close()
                connection.close()
    
    
    @classmethod
    def load_all_audit_logs(cls):
        connection = connect_to_database()
        audit_logs = []
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT account_number, account_holder_name, action, amount, timestamp FROM audit ORDER BY timestamp DESC")
                results = cursor.fetchall()
                for row in results:
                    audit_logs.append(cls(row[0], row[1], row[2], row[3], row[4]))
            except Exception as e:
                print(f"Error loading logs: {e}")
            finally:
                cursor.close()
                connection.close()
        return audit_logs
    
    @classmethod
    def delete_audit_logs_for_account(cls, account_number):
        connection = connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM audit WHERE account_number = %s", (account_number,))
                connection.commit()
            except Exception as e:
                print(f"Error deleting logs: {e}")
            finally:
                cursor.close()
                connection.close()

# ==========================================
# ADMIN CLI MENUS
# ==========================================
def admin_login():
    """Handles secure admin authentication."""
    print("\n--- Administrator Login ---")
    username = input("Enter Admin Username: ").strip()
    password = getpass.getpass("Enter Admin Password: ").strip()

    connection = connect_to_database()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT password_hash FROM admins WHERE username = %s", (username,))
            result = cursor.fetchone()
            
            if result and verify_password(password, result[0]):
                print("\nLogin Successful!")
                return True
            else:
                print("\nInvalid username or password.")
                return False
        except Exception as e:
            print(f"Database error during login: {e}")
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def admin_menu():
    """The secure menu only accessible after login."""
    setup_first_admin() # Ensure the table exists
    
    if not admin_login():
        return # Kick them out if login fails

    while True:
        print("\n--- Admin Control Panel ---")
        print("1. View Specific Account Logs")
        print("2. View All Audit Logs")
        print("3. Delete Audit Logs for Specific Account")
        print("4. Create New Admin")
        print("0. Logout")
        
        choice = input("Enter your choice: ").strip()

        if choice == '1':
            account_number = input("Enter Account Number: ").strip()
            logs = Audit.load_specific_audit_logs(account_number)
            if logs:
                for log in logs:
                    print(f"Acct: {log.get_account_number()} | Action: {log.get_action()} | Amount: {log.get_amount()} | Time: {log.get_timestamp()}")
            else:
                print("No logs found.")
        elif choice == '2':
            logs = Audit.load_all_audit_logs()
            if logs:
                for log in logs:
                    print(f"Acct: {log.get_account_number()} | Action: {log.get_action()} | Amount: {log.get_amount()} | Time: {log.get_timestamp()}")
            else:
                print("No logs found.")
        
        elif choice == '3':
            account_number = input("Enter Account Number: ").strip()
            Audit.delete_audit_logs_for_account(account_number)
        
        elif choice == '4':
            username = input("Enter new admin username: ").strip()
            password = input("Enter new admin password: ").strip()
            Audit.create_new_admin(username, password)
        elif choice == '0':
            print("Logging out of Admin Panel...")
            break
        else:
            print("Invalid choice.")