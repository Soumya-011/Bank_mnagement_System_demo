<div align="center">
  
  <h1>🏦 Secure Bank Management System</h1>
  
  <p>
    <strong>A full-stack, interactive Python banking dashboard featuring secure bcrypt password hashing, data analytics, transaction audit logs, and distinct portals for customer and administrator management.</strong>
  </p>

  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Framework-Streamlit-FF4B4B.svg" alt="Streamlit">
  <img src="https://img.shields.io/badge/Database-PostgreSQL-336791.svg" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Security-bcrypt-success.svg" alt="Security">

</div>

---

## ✨ Features

**For Customers:**
* **Interactive Dashboard:** Modern web UI to manage funds effortlessly.
* **Secure Auth:** PINs are safely hashed using industry-standard `bcrypt`.
* **Account Management:** Deposit, withdraw, and transfer money to other accounts in real-time.
* **Transaction History:** View and download your personal account audit logs as a CSV.

**For Administrators:**
* **Global Audit Logging:** Track every transaction and account modification across the entire system.
* **Data Analytics:** View monthly activity summaries, highly engaged users, and high-value accounts.
* **System Maintenance:** Export global logs, securely wipe old records, and manage customer usernames.
* **Admin Management:** Create new administrator credentials easily.

---

## 🛠️ Prerequisites

* [Python 3.8+](https://www.python.org/downloads/)
* A SQL Database (Configured for **PostgreSQL / pgAdmin 4**)

---

## 🚀 Setup & Installation

**1. Clone the repository:**
```bash
git clone [https://github.com/Soumya-011/Bank_mnagement_System_demo.git](https://github.com/Soumya-011/Bank_mnagement_System_demo.git)
cd Bank_mnagement_System_demo

Install required dependencies:

Bash
pip install -r requirements.txt
3. Configure your Database:
Create a file named Database.py in the root directory. Add the following code and update the placeholders with your PostgreSQL credentials:

Python
import psycopg2
def connect_to_database():
    try:
        return psycopg2.connect(
            user="postgres",              
            password="your_password",     
            host="127.0.0.1",             
            port="5432",                  
            database="your_database_name" 
        )
    except Exception as e:
        print(f"Database connection error: {e}")
        return None
(Make sure Database.py is in your .gitignore file!)

4. Generate Mock Data (Optional but Recommended):
To populate the database with realistic customers and transaction histories to test the analytics dashboard, run:

Bash
python seed_data.py
(This creates 60 users and 200 random transactions. All mock user PINs are set to 1234).

5. Run the Web Application:

Bash
streamlit run app.py
💻 Usage Navigation
Customer Portal: Create a new account or log in with your generated Account Number and PIN.

Admin Portal: Log in to view system analytics. (Default initial credentials -> Username: admin | Password: admin123)

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.