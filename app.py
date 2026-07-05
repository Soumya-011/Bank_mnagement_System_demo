import streamlit as st
import pandas as pd
from decimal import Decimal
from User import Account
from Admin import Audit, setup_first_admin
from Database import connect_to_database

# ==========================================
# PAGE CONFIGURATION & STATE
# ==========================================
st.set_page_config(page_title="Secure Bank System", page_icon="🏦", layout="centered")

# Initialize session state variables to remember who is logged in
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ==========================================
# HELPER FUNCTIONS & NEW DB QUERIES
# ==========================================
def verify_admin(username, password):
    from Admin import verify_password
    connection = connect_to_database()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT password_hash FROM admins WHERE username = %s", (username,))
            result = cursor.fetchone()
            if result and verify_password(password, result[0]):
                return True
        finally:
            cursor.close()
            connection.close()
    return False

def convert_logs_to_csv(logs):
    """Converts a list of Audit log objects into a downloadable CSV string."""
    if not logs:
        return ""
    data = [{
        "Date & Time": log.get_timestamp().strftime('%Y-%m-%d %H:%M:%S'),
        "Account Number": log.get_account_number(),
        "Action": log.get_action(),
        "Amount ($)": f"{log.get_amount():.2f}"
    } for log in logs]
    df = pd.DataFrame(data)
    return df.to_csv(index=False).encode('utf-8')

def admin_change_username(account_number, new_name):
    """Allows admins to update a customer's name."""
    connection = connect_to_database()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE accounts SET account_holder_name = %s WHERE account_number = %s", (new_name, account_number))
            if cursor.rowcount > 0:
                connection.commit()
                return True
        finally:
            cursor.close()
            connection.close()
    return False

def admin_delete_old_audits():
    """Deletes audit records older than 5 years."""
    connection = connect_to_database()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM audit WHERE timestamp < NOW() - INTERVAL '5 years'")
            deleted_count = cursor.rowcount
            connection.commit()
            return deleted_count
        finally:
            cursor.close()
            connection.close()
    return 0

def get_monthly_report():
    """Generates a summary of activity for the current month."""
    connection = connect_to_database()
    report = {"deposits": 0, "withdrawals": 0, "active_accounts": 0}
    if connection:
        try:
            cursor = connection.cursor()
            
            # FIX: Double the %% in %%deposit%%
            cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM audit WHERE action ILIKE '%%deposit%%' AND date_trunc('month', timestamp) = date_trunc('month', CURRENT_DATE)")
            report["deposits"] = cursor.fetchone()[0]
            
            # FIX: Double the %% in %%withdraw%%
            cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM audit WHERE action ILIKE '%%withdraw%%' AND date_trunc('month', timestamp) = date_trunc('month', CURRENT_DATE)")
            report["withdrawals"] = cursor.fetchone()[0]
            
            # Distinct Active Accounts this month
            cursor.execute("SELECT COUNT(DISTINCT account_number) FROM audit WHERE date_trunc('month', timestamp) = date_trunc('month', CURRENT_DATE)")
            report["active_accounts"] = cursor.fetchone()[0]
        finally:
            cursor.close()
            connection.close()
    return report

def get_high_value_accounts(threshold):
    """Finds accounts with total deposits over a specific threshold."""
    connection = connect_to_database()
    results = []
    if connection:
        try:
            cursor = connection.cursor()
            query = """
            SELECT a.account_number, a.account_holder_name, SUM(au.amount) as total_deposits
            FROM accounts a
            JOIN audit au ON a.account_number = au.account_number
            WHERE au.action ILIKE '%%deposit%%' 
            
            GROUP BY a.account_number, a.account_holder_name
            HAVING SUM(au.amount) >= %s
            ORDER BY total_deposits DESC
            """
            cursor.execute(query, (threshold,))
            results = cursor.fetchall()
        finally:
            cursor.close()
            connection.close()
    return results

def get_active_accounts_query():
    """Lists accounts with more than 5 total transactions."""
    connection = connect_to_database()
    results = []
    if connection:
        try:
            cursor = connection.cursor()
            query = """
            SELECT a.account_number, a.account_holder_name, COUNT(au.id) as tx_count
            FROM accounts a
            JOIN audit au ON a.account_number = au.account_number
            GROUP BY a.account_number, a.account_holder_name
            HAVING COUNT(au.id) > 5
            ORDER BY tx_count DESC
            """
            cursor.execute(query)
            results = cursor.fetchall()
        finally:
            cursor.close()
            connection.close()
    return results

def get_most_active_user():
    """Shows the single account with the most transactions."""
    connection = connect_to_database()
    result = None
    if connection:
        try:
            cursor = connection.cursor()
            query = """
            SELECT a.account_number, a.account_holder_name, COUNT(au.id) as tx_count
            FROM accounts a
            JOIN audit au ON a.account_number = au.account_number
            GROUP BY a.account_number, a.account_holder_name
            ORDER BY tx_count DESC
            LIMIT 1
            """
            cursor.execute(query)
            result = cursor.fetchone()
        finally:
            cursor.close()
            connection.close()
    return result

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("🏦 Main Menu")
portal = st.sidebar.radio("Select Portal:", ["Customer Portal", "Administrator Portal"])

# ==========================================
# 1. CUSTOMER PORTAL
# ==========================================
if portal == "Customer Portal":
    st.title("Customer Portal")

    if st.session_state.current_user is None:
        tab1, tab2 = st.tabs(["Login", "Create Account"])

        with tab1:
            st.subheader("Account Login")
            acc_num = st.text_input("Account Number")
            pin = st.text_input("4-Digit PIN", type="password") 
            
            if st.button("Login", use_container_width=True):
                account = Account.load_from_database(acc_num, pin)
                if account:
                    st.session_state.current_user = account
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Invalid Account Number or PIN.")

        with tab2:
            st.subheader("Open a New Account")
            new_name = st.text_input("Full Name")
            new_pin = st.text_input("Create 4-Digit PIN", type="password")
            new_deposit = st.number_input("Initial Deposit ($)", min_value=0.00, value=0.00, step=10.00)
            
            if st.button("Create Account", use_container_width=True):
                if not new_name:
                    st.warning("Name cannot be empty.")
                elif not (new_pin.isdigit() and len(new_pin) == 4):
                    st.warning("PIN must be exactly 4 digits.")
                else:
                    account = Account.create_account(new_name, new_pin, Decimal(new_deposit))
                    if account:
                        st.success(f"Account Created! Your Account Number is: **{account.get_account_number()}**")
                        Audit.save_to_database(account.get_account_number(), new_name, "Account Created", Decimal(new_deposit))
                    else:
                        st.error("Failed to create account.")

    else:
        user = st.session_state.current_user
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"### Welcome back, {user.get_account_holder_name()}")
        with col2:
            if st.button("Logout"):
                st.session_state.current_user = None
                st.rerun()

        st.metric("Current Balance", f"${user.get_balance():.2f}")
        st.divider()

        d_tab1, d_tab2, d_tab3, d_tab4 = st.tabs(["Transact", "Transfer", "History", "Settings"])

        with d_tab1:
            st.subheader("Deposit or Withdraw")
            amount = st.number_input("Amount ($)", min_value=0.01, value=10.00, step=10.00)
            col_d, col_w = st.columns(2)
            if col_d.button("Deposit", use_container_width=True):
                if user.deposit(Decimal(amount)):
                    user.update_in_database()
                    Audit.save_to_database(user.get_account_number(), user.get_account_holder_name(), "Deposit", Decimal(amount))
                    st.success(f"Deposited ${amount:.2f} successfully!")
                    st.rerun()
            if col_w.button("Withdraw", use_container_width=True):
                if user.withdraw(Decimal(amount)):
                    user.update_in_database()
                    Audit.save_to_database(user.get_account_number(), user.get_account_holder_name(), "Withdrawal", Decimal(amount))
                    st.success(f"Withdrew ${amount:.2f} successfully!")
                    st.rerun()
                else:
                    st.error("Insufficient funds.")

        with d_tab2:
            st.subheader("Transfer Funds")
            receiver_acc = st.text_input("Recipient Account Number")
            transfer_amount = st.number_input("Transfer Amount ($)", min_value=0.01, value=10.00, step=10.00)
            if st.button("Send Money", use_container_width=True):
                if Account.process_transfer(user, Decimal(transfer_amount), receiver_acc):
                    st.success("Transfer successful!")
                    st.rerun()
                else:
                    st.error("Transfer failed. Check recipient account and your balance.")

        with d_tab3:
            st.subheader("Recent Transactions")
            logs = Audit.load_specific_audit_logs(user.get_account_number())
            if logs:
                # Add Download/Print Button
                csv = convert_logs_to_csv(logs)
                st.download_button(label="📥 Download/Print Transaction History (CSV)", data=csv, file_name="my_transactions.csv", mime="text/csv")
                st.write("") # Spacer
                for log in logs:
                    st.text(f"[{log.get_timestamp().strftime('%Y-%m-%d %H:%M')}] {log.get_action()} | ${log.get_amount()}")
            else:
                st.info("No transaction history found.")

        with d_tab4:
            st.subheader("Account Settings")
            new_pin = st.text_input("New 4-Digit PIN", type="password")
            if st.button("Update PIN"):
                if new_pin.isdigit() and len(new_pin) == 4:
                    user.set_pin(new_pin)
                    user.update_in_database()
                    st.success("PIN updated successfully.")
                else:
                    st.warning("PIN must be 4 digits.")

# ==========================================
# 2. ADMINISTRATOR PORTAL
# ==========================================
elif portal == "Administrator Portal":
    st.title("Admin Control Panel")
    setup_first_admin()

    if not st.session_state.admin_logged_in:
        st.subheader("Secure Login")
        admin_user = st.text_input("Username")
        admin_pass = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if verify_admin(admin_user.lower(), admin_pass):
                st.session_state.admin_logged_in = True
                st.success("Authenticated.")
                st.rerun()
            else:
                st.error("Invalid Admin Credentials.")
    else:
        if st.button("Logout Admin"):
            st.session_state.admin_logged_in = False
            st.rerun()
            
        st.divider()
        a_tab1, a_tab2, a_tab3, a_tab4, a_tab5 = st.tabs(["Global Logs", "Specific Logs", "Data Analytics", "Manage Accounts", "Manage Admins"])
        
        with a_tab1:
            st.subheader("Global Audit Logs")
            all_logs = Audit.load_all_audit_logs()
            if all_logs:
                csv = convert_logs_to_csv(all_logs)
                st.download_button(label="📥 Download All System Logs (CSV)", data=csv, file_name="global_audit_logs.csv", mime="text/csv")
                for log in all_logs[:50]: # Showing top 50 to prevent UI lag
                    st.text(f"[{log.get_timestamp().strftime('%Y-%m-%d %H:%M')}] Acct: {log.get_account_number()} | Action: {log.get_action()} | ${log.get_amount()}")
            else:
                st.info("No logs found in the system.")

        with a_tab2:
            st.subheader("Search Specific Account Logs")
            search_acc = st.text_input("Enter Account Number to Search:")
            if st.button("Search Logs"):
                if search_acc:
                    spec_logs = Audit.load_specific_audit_logs(search_acc)
                    if spec_logs:
                        csv = convert_logs_to_csv(spec_logs)
                        st.download_button(label=f"📥 Download Logs for {search_acc} (CSV)", data=csv, file_name=f"logs_{search_acc}.csv", mime="text/csv")
                        for log in spec_logs:
                            st.text(f"[{log.get_timestamp().strftime('%Y-%m-%d %H:%M')}] Action: {log.get_action()} | ${log.get_amount()}")
                    else:
                        st.warning("No logs found for this account.")

        with a_tab3:
            st.subheader("Bank Data Analytics")
            
            # 1. Monthly Report
            st.markdown("#### 📊 Current Month Summary")
            report = get_monthly_report()
            r_col1, r_col2, r_col3 = st.columns(3)
            r_col1.metric("Total Deposits", f"${report['deposits']:.2f}")
            r_col2.metric("Total Withdrawals", f"${report['withdrawals']:.2f}")
            r_col3.metric("Active Accounts", report['active_accounts'])
            
            st.divider()
            
            # 2. Most Active User
            st.markdown("#### 🏆 Most Active User")
            top_user = get_most_active_user()
            if top_user:
                st.info(f"**{top_user[1]}** (Acct: {top_user[0]}) with **{top_user[2]}** transactions.")
            else:
                st.write("Not enough data.")
            
            st.divider()
            
            # 3. High Value Accounts
            st.markdown("#### 💰 High Value Accounts")
            threshold = st.number_input("Set Deposit Threshold ($):", min_value=0.00, value=10000.00, step=1000.00)
            high_value_accs = get_high_value_accounts(Decimal(threshold))
            if high_value_accs:
                df_high = pd.DataFrame(high_value_accs, columns=["Account Number", "Name", "Total Deposits"])
                st.dataframe(df_high, use_container_width=True)
            else:
                st.write(f"No accounts found with total deposits over ${threshold:.2f}")
                
            st.divider()
            
            # 4. Active Accounts (>5 tx)
            st.markdown("#### 🔥 Highly Engaged Accounts (> 5 Transactions)")
            active_accs = get_active_accounts_query()
            if active_accs:
                df_active = pd.DataFrame(active_accs, columns=["Account Number", "Name", "Total Transactions"])
                st.dataframe(df_active, use_container_width=True)
            else:
                st.write("No accounts have more than 5 transactions yet.")

        with a_tab4:
            st.subheader("Manage Customer Accounts")
            
            # Change Username
            st.markdown("**Change Customer Name**")
            update_acc_num = st.text_input("Customer Account Number")
            new_holder_name = st.text_input("New Full Name")
            if st.button("Update Name"):
                if admin_change_username(update_acc_num, new_holder_name):
                    st.success("Customer name updated successfully.")
                else:
                    st.error("Failed to update. Verify account number.")
                    
            st.divider()
            
            # Delete Old Audits
            st.markdown("**System Maintenance**")
            st.warning("This will permanently remove all transaction logs older than 5 years.")
            if st.button("Delete Old Audit Logs"):
                deleted = admin_delete_old_audits()
                st.success(f"Cleanup complete. Removed {deleted} old records.")

        with a_tab5:
            st.subheader("Create New Administrator")
            new_admin_user = st.text_input("New Admin Username")
            new_admin_pass = st.text_input("New Admin Password", type="password")
            if st.button("Create Admin"):
                if new_admin_user and new_admin_pass:
                    Audit.create_new_admin(new_admin_user.lower(), new_admin_pass)
                    st.success(f"Admin '{new_admin_user.lower()}' created successfully.")
                else:
                    st.warning("Both fields are required.")