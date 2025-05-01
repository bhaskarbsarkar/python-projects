# Progressive Computers Student CRM

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-orange.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A simple Customer Relationship Management (CRM) application built with Streamlit, designed for small educational enterprises like "Progressive Computers" to manage student data efficiently.

## Features

*   **Student Data Management:**
    *   Add new student records with comprehensive details (Personal Info, Contact, Course, Fees).
    *   View all student records in a tabular format.
    *   Edit existing student records.
    *   Delete student records.
*   **Fee Tracking:**
    *   Record Total Fees, Fees Paid, and Payment Mode (Online, Cheque, Cash, Other).
    *   Automatically calculates and displays Balance Fees.
    *   Dedicated tab to view students with outstanding balances.
*   **Receipt Generation:**
    *   View formatted fee receipt details directly within the app.
    *   Download fee receipts as clean PDF files.
*   **Data Persistence:**
    *   Uses local SQLite databases (`student_crm.db`, `audit_log.db`) for data storage. No external database setup required.
*   **Audit Trail:**
    *   Logs all significant actions (Add, Edit, Delete) to an audit database.
    *   Admin panel (password-protected) to view audit logs.
*   **Backup:**
    *   Automatically creates daily CSV backups of the student and audit log databases in the `backups` folder.
*   **Security:**
    *   Password protection for accessing the main application.
    *   Separate password protection for the admin panel.

## Technologies Used

*   **Python:** Core programming language.
*   **Streamlit:** Framework for building the interactive web application UI.
*   **Pandas:** For data manipulation and display.
*   **SQLite:** Embedded database for local data storage.
*   **fpdf2:** Library for generating PDF receipts.

## Setup and Installation

1.  **Prerequisites:**
    *   Python 3.7 or higher installed.
    *   `pip` (Python package installer).

2.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

3.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Ensure you have a `requirements.txt` file containing `streamlit`, `pandas`, and `fpdf2`)*

## Running the Application

1.  Navigate to the project directory in your terminal.
2.  Make sure your virtual environment is activated (if you created one).
3.  Run the Streamlit application:
    ```bash
    streamlit run main.py
    ```
4.  The application will open in your default web browser.

## Configuration

*   **Application Password:** The default password to access the app is `"password"`. This can be changed by modifying the `APP_PASSWORD` variable in `main.py`.
*   **Admin Password:** The default password for the admin panel (Audit Logs) is `"admin"`. This can be changed by modifying the `ADMIN_PASSWORD` variable in `main.py`.
*   **Database Files:** `student_crm.db` (for student data) and `audit_log.db` (for logs) will be automatically created in the same directory as `main.py` on the first run if they don't exist.
*   **Backups:** CSV backups are stored in the `backups` folder, which is created automatically if it doesn't exist.

## Usage

1.  Enter the application password when prompted.
2.  Use the tabs (`View All`, `Add Student`, `Edit / Delete`, `Print Receipt`, `Balance Fees`) to navigate through different functionalities.
3.  To access the audit logs, use the "Admin Access" section in the sidebar and enter the admin password.

## License

This project is licensed under the MIT License - see the LICENSE file for details (if you choose to add one).