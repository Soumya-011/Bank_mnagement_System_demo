import random
import string
import getpass
from Database import connect_to_database
from Admin import Audit, hash_password, verify_password
from decimal import Decimal

class Account:
    def __init__(self, name="", pin="", account_number=""):
        self.__account_number = account_number if account_number else self.__generate_account_number()
        self.__account_holder_name = name
        # We only hash the PIN here if it's a new account creation. 
        # When loading from DB, we set it directly in load_from_database.
        self.__pin_hash = hash_password(pin) if pin else "" 
        self.__balance = 0.00

    @staticmethod
    def __generate_account_number():
        later_part = ''.join(random.choices(string.ascii_uppercase, k=4))
        number_part = ''.join(random.choices(string.digits, k=8))
        return later_part + number_part

    def get_account_number(self): return self.__account_number
    def get_account_holder_name(self): return self.__account_holder_name
    def get_balance(self): return self.__balance

    def deposit(self, amount):
        if amount > 0:
            self.__balance += amount
            return True
        return False

    def withdraw(self, amount):
        if 0 < amount <= self.__balance:
            self.__balance -= amount
            return True
        return False

    def set_pin(self, new_pin):
        """Hashes and sets a new PIN for the account."""
        self.__pin_hash = hash_password(new_pin)
    
    def save_to_database(self):
        """Saves a NEW account to the database."""
        connection = connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                insert_query = """
                INSERT INTO accounts (account_number, account_holder_name, pin, balance)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (self.__account_number, self.__account_holder_name, self.__pin_hash, self.__balance))
                connection.commit()
                return True
            except Exception as e:
                print(f"Error saving account: {e}")
                return False 
            finally:
                cursor.close()
                connection.close() 

    def update_in_database(self):
        """Updates balance and PIN for an existing account."""
        connection = connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                # Update the query to include the pin
                update_query = """
                UPDATE accounts 
                SET balance = %s, pin = %s 
                WHERE account_number = %s
                """
                # Pass the pin_hash into the execute variables
                cursor.execute(update_query, (self.__balance, self.__pin_hash, self.__account_number))
                connection.commit()
                return True
            except Exception as e:
                print(f"Error updating account: {e}")
                return False
            finally:
                cursor.close()
                connection.close()

    @classmethod
    def create_account(cls, name, pin, balance=0.00):
        # Fixed: We properly instantiate the class and then save it
        account = cls(name, pin)
        account.__balance = balance
        if account.save_to_database():
            return account
        return None
        
    @classmethod
    def load_from_database(cls, account_number, pin):
        connection = connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT account_holder_name, pin, balance FROM accounts WHERE account_number = %s", (account_number,))
                result = cursor.fetchone()
                
                if result:
                    stored_name, stored_hash, stored_balance = result
                    if verify_password(pin, stored_hash):
                        account = cls(stored_name, "", account_number)
                        account.__pin_hash = stored_hash
                        account.__balance = stored_balance
                        return account
                    else:
                        print("Invalid PIN.")
                else:
                    print("Account not found.")
            except Exception as e:
                print(f"Database error: {e}")
            finally:
                cursor.close()
                connection.close()
        return None
    
    @classmethod
    def process_transfer(cls, sender_account, amount, receiver_account_number):
        """Handles the logic of moving money securely between two accounts."""
        connection = connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                
                # 1. Verify receiver exists
                cursor.execute("SELECT account_holder_name FROM accounts WHERE account_number = %s", (receiver_account_number,))
                receiver = cursor.fetchone()
                
                if not receiver:
                    print("Error: Receiving account does not exist.")
                    return False
                    
                # 2. Attempt to withdraw from sender
                if sender_account.withdraw(amount):
                    # 3. If withdrawal succeeds, deposit to receiver via SQL
                    cursor.execute("UPDATE accounts SET balance = balance + %s WHERE account_number = %s", (amount, receiver_account_number))
                    
                    # 4. Update the sender's balance in the DB
                    sender_account.update_in_database()
                    
                    connection.commit()
                    
                    # 5. Log for both users
                    Audit.save_to_database(sender_account.get_account_number(), sender_account.get_account_holder_name(), f"Transfer Out to {receiver_account_number}", amount)
                    Audit.save_to_database(receiver_account_number, receiver[0], f"Transfer In from {sender_account.get_account_number()}", amount)
                    return True
                else:
                    print("Insufficient funds for transfer.")
                    return False
                    
            except Exception as e:
                print(f"Transfer error: {e}")
                connection.rollback() # Revert any partial changes if it crashes
            finally:
                cursor.close()
                connection.close()
        return False
    
    
    @classmethod
    def delete_account(cls, account_number, pin):
        connection = connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT account_holder_name, pin FROM accounts WHERE account_number = %s", (account_number,))
                result = cursor.fetchone()
                
                if result:
                    stored_name, stored_hash = result
                    if verify_password(pin, stored_hash):
                        
                        # 1. First, save the deletion to the audit log BEFORE deleting the account
                        Audit.save_to_database(account_number, stored_name, "Account Permanently Deleted", 0)
                        
                        # 2. Then, safely delete the account from the accounts table
                        cursor.execute("DELETE FROM accounts WHERE account_number = %s", (account_number,))
                        connection.commit()
                        
                        print("Account deleted successfully. Transaction history retained for administrative audit.")
                        return True
                    else:
                        print("Invalid PIN.")
                else:
                    print("Account not found.")
            except Exception as e:
                print(f"Database error: {e}")
            finally:
                cursor.close()
                connection.close()
        return False

# ==========================================
# USER CLI FUNCTIONS
# ==========================================
def create_account_cli():
    name = input("Enter your name: ").strip()
    pin = input("Enter a 4-digit PIN: ").strip()
    if not (pin.isdigit() and len(pin) == 4):
        print("Invalid PIN. Must be 4 digits.")
        return
        
    balance = Decimal(input("Enter initial deposit: ") or "0")
    
    account = Account.create_account(name, pin, balance)
    if account:
        print(f"Success! Account Number: {account.get_account_number()}")
        Audit.save_to_database(account.get_account_number(), name, "Account Created", balance)

def deposit_money_cli():
    acc_num = input("Enter account number: ").strip()
    # Replaced input() with getpass.getpass()
    pin = getpass.getpass("Enter PIN: ").strip() 
    
    account = Account.load_from_database(acc_num, pin)
    if account:
        amount = Decimal(input("Enter deposit amount: "))
        if account.deposit(amount):
            account.update_in_database()
            print(f"Deposited {amount}. New Balance: {account.get_balance()}")
            Audit.save_to_database(account.get_account_number(), account.get_account_holder_name(), "Deposit", amount)
        else:
            print("Invalid amount.")

def withdraw_money_cli():
    acc_num = input("Enter account number: ").strip()
    pin = getpass.getpass("Enter PIN: ").strip()
    
    account = Account.load_from_database(acc_num, pin)
    if account:
        amount = Decimal(input("Enter withdrawal amount: "))
        if account.withdraw(amount):
            account.update_in_database()
            print(f"Withdrew {amount}. New Balance: {account.get_balance()}")
            Audit.save_to_database(account.get_account_number(), account.get_account_holder_name(), "Withdrawal", amount)
        else:
            print("Invalid amount or insufficient funds.")

def transfer_money_cli():
    sender_acc_num = input("Enter your account number: ").strip()
    sender_pin = getpass.getpass("Enter your PIN: ").strip()
    
    sender_account = Account.load_from_database(sender_acc_num, sender_pin)
    if not sender_account:
        return
    
    receiver_acc_num = input("Enter recipient's account number: ").strip()
    amount = Decimal(input("Enter transfer amount: "))
    
    if Account.process_transfer(sender_account, amount, receiver_acc_num):
        print(f"Transferred {amount} to {receiver_acc_num}. New Balance: {sender_account.get_balance()}")
    else:
        print("Transfer failed.")


def check_balance_cli():
    acc_num = input("Enter account number: ").strip()
    pin = getpass.getpass("Enter PIN: ").strip()
    
    account = Account.load_from_database(acc_num, pin)
    if account:
        print(f"Current Balance: {account.get_balance()}")
        Audit.save_to_database(account.get_account_number(), account.get_account_holder_name(), "Balance Check", 0)

def check_account_details_cli():
    acc_num = input("Enter account number: ").strip()
    pin = getpass.getpass("Enter PIN: ").strip()
    
    account = Account.load_from_database(acc_num, pin)
    if account:
        print(f"Account Number: {account.get_account_number()}")
        print(f"Account Holder: {account.get_account_holder_name()}")
        print(f"Balance: {account.get_balance()}")
        Audit.save_to_database(account.get_account_number(), account.get_account_holder_name(), "Account Details Check", 0)

def check_transaction_history_cli():
    acc_num = input("Enter account number: ").strip()
    pin = getpass.getpass("Enter PIN: ").strip()
    
    account = Account.load_from_database(acc_num, pin)
    if account:
        logs = Audit.load_specific_audit_logs(account.get_account_number())
        if logs:
            for log in logs:
                print(f"Action: {log.get_action()} | Amount: {log.get_amount()} | Time: {log.get_timestamp()}")
        else:
            print("No transaction history found.")
        Audit.save_to_database(account.get_account_number(), account.get_account_holder_name(), "Transaction History Check", 0)

def change_pin_cli():
    acc_num = input("Enter account number: ").strip()
    old_pin = input("Enter current PIN: ").strip()
    
    account = Account.load_from_database(acc_num, old_pin)
    if account:
        new_pin = input("Enter new 4-digit PIN: ").strip()
        if not (new_pin.isdigit() and len(new_pin) == 4):
            print("Invalid PIN. Must be 4 digits.")
            return
        
        account.set_pin(new_pin)
        account.update_in_database()
        print("PIN changed successfully.")
        Audit.save_to_database(account.get_account_number(), account.get_account_holder_name(), "PIN Change", 0)

def delete_account_cli():
    acc_num = input("Enter account number: ").strip()
    pin = input("Enter PIN: ").strip()
    
    # The logging is now handled securely inside the class method!
    Account.delete_account(acc_num, pin)

def user_menu():
    while True:
        print("\n--- Customer Portal ---")
        print("1. Create Account")
        print("2. Deposit Money")
        print("3. Withdraw Money")
        print("4. Check Balance")
        print("5. Check Account Details")
        print("6. Check Transaction History")
        print("7. Change PIN")
        print("8. Delete Account")
        print("9. Transfer Money to Another Account")
        print("0. Return to Main Menu")
        
        choice = input("Enter choice: ").strip()
        if choice == '1':
            create_account_cli()
        elif choice == '2':
            deposit_money_cli()
        elif choice == '3':
            withdraw_money_cli()
        elif choice == '4':
            check_balance_cli()
        elif choice == '5':
            check_account_details_cli()
        elif choice == '6':
            check_transaction_history_cli()
        elif choice == '7':
            change_pin_cli()
        elif choice == '8':
            delete_account_cli()
        elif choice == '9':
            transfer_money_cli()
        elif choice == '0':
            break
        else:
            print("Invalid choice.")