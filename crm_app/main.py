import streamlit as st
import pandas as pd
from datetime import datetime, date # Import date
import uuid # To generate unique IDs
import sqlite3
import os
import json # For loading course data
from fpdf import FPDF # Import FPDF

# --- Configuration ---
APP_TITLE = "Progressive Computers Student CRM"
APP_ICON = "🎓"
DB_FILE = "student_crm.db"
AUDIT_DB_FILE = "audit_log.db"
COURSES_FILE = "courses.json" # Path to your courses JSON file
BACKUP_DIR = "backups"
ADMIN_PASSWORD = "admin" # Replace with a more secure method if needed (e.g., environment variable)
APP_PASSWORD = "password" # Password for general app access

# --- Database Setup (SQLite) ---

# --- Student DB ---
# Define expected columns and their rough types for DB creation
# Use TEXT for flexibility, especially with IDs, dates, and potentially empty numbers
EXPECTED_COLUMNS_TYPES = {
    'Record ID': 'TEXT PRIMARY KEY',
    'Student Name': 'TEXT NOT NULL',
    'Father Name': 'TEXT',
    'Mother Name': 'TEXT',
    'Course Name': 'TEXT NOT NULL',
    'Fees Detail': 'TEXT',
    'Date of Birth': 'TEXT', # Store as ISO format string YYYY-MM-DD
    'Address': 'TEXT',
    'Aadhar Card No': 'TEXT',
    'Mobile No': 'TEXT NOT NULL',
    'Email Address': 'TEXT',
    'Total Fees': 'REAL DEFAULT 0', # Use REAL for potential decimal values
    'Fees Paid': 'REAL DEFAULT 0',
    'Balance Fees': 'REAL DEFAULT 0',
    'Course Enrollment Date': 'TEXT',
    'Enrollment No': 'TEXT' # New column for enrollment number
}
EXPECTED_COLUMNS = list(EXPECTED_COLUMNS_TYPES.keys())

def init_db(db_path=DB_FILE):
    """Initializes the SQLite database and table if they don't exist."""
    # Use context manager for automatic commit/close
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Check if the new column exists and add it if it doesn't
        cursor.execute("PRAGMA table_info(students)")
        columns = [info[1] for info in cursor.fetchall()]

        # Add columns if they don't exist
        for col_name, col_type in [('Course Enrollment Date', 'TEXT'), ('Enrollment No', 'TEXT')]:
            if col_name not in columns:
                try:
                    cursor.execute(f'ALTER TABLE students ADD COLUMN "{col_name}" {col_type}')
                    print(f"Added '{col_name}' column to students table.") # Optional: log this
                except Exception as e:
                    st.error(f"Failed to add '{col_name}' column: {e}")
        conn.commit() # Commit after all potential ALTER TABLE statements

        # Create table dynamically based on EXPECTED_COLUMNS_TYPES
        columns_sql = ", ".join([f'"{col}" {dtype}' for col, dtype in EXPECTED_COLUMNS_TYPES.items()])
        create_table_sql = f"CREATE TABLE IF NOT EXISTS students ({columns_sql})"
        cursor.execute(create_table_sql)

# --- Audit Log DB ---
AUDIT_COLUMNS_TYPES = {
    'Log ID': 'INTEGER PRIMARY KEY AUTOINCREMENT',
    'Timestamp': 'TEXT NOT NULL',
    'Action': 'TEXT NOT NULL', # e.g., ADD, EDIT, DELETE
    'Record ID': 'TEXT',      # Student Record ID affected
    'Details': 'TEXT'         # e.g., "Student Added", "Updated fields: Name, Fees Paid"
}

def init_audit_db(db_path=AUDIT_DB_FILE):
    """Initializes the Audit Log SQLite database and table."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        columns_sql = ", ".join([f'"{col}" {dtype}' for col, dtype in AUDIT_COLUMNS_TYPES.items()])
        create_table_sql = f"CREATE TABLE IF NOT EXISTS logs ({columns_sql})"
        cursor.execute(create_table_sql)

def log_action(action: str, record_id: str = None, details: str = ""):
    """Logs an action to the audit database."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_data = {
        'Timestamp': timestamp,
        'Action': action,
        'Record ID': record_id if record_id else 'N/A',
        'Details': details
    }
    try:
        with sqlite3.connect(AUDIT_DB_FILE) as conn:
            cursor = conn.cursor()
            cols = ', '.join([f'"{k}"' for k in log_data.keys()])
            placeholders = ', '.join(['?'] * len(log_data))
            sql = f"INSERT INTO logs ({cols}) VALUES ({placeholders})"
            values_tuple = tuple(log_data.values())
            cursor.execute(sql, values_tuple)
    except Exception as e:
        st.error(f"Failed to write audit log: {e}") # Log error but don't stop app

# --- Authentication Function ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == APP_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password.
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Enter App Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Enter App Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True
# --- Utility Functions ---
def load_data() -> pd.DataFrame:
    """Loads data from Google Sheets into a Pandas DataFrame."""
    conn = None # Initialize conn to None
    try:
        conn = sqlite3.connect(DB_FILE)
        # Fetch all data from the students table
        query = "SELECT * FROM students"
        data = pd.read_sql_query(query, conn)

        # Convert relevant columns to appropriate types
        data['Date of Birth'] = pd.to_datetime(data['Date of Birth'], errors='coerce').dt.date
        data['Course Enrollment Date'] = pd.to_datetime(data['Course Enrollment Date'], errors='coerce').dt.date
        # Enrollment No is TEXT, so no specific conversion needed here unless formatting is required
        data['Total Fees'] = pd.to_numeric(data['Total Fees'], errors='coerce').fillna(0)
        data['Fees Paid'] = pd.to_numeric(data['Fees Paid'], errors='coerce').fillna(0)
        data['Balance Fees'] = pd.to_numeric(data['Balance Fees'], errors='coerce').fillna(0)

        # Fill NaN values in object columns with empty strings for display
        for col in data.select_dtypes(include='object').columns:
            data[col] = data[col].fillna('')

        # Reindex to ensure correct order and all expected columns are present.
        # Missing columns will be added with NaN, then filled with empty string.
        data = data.reindex(columns=EXPECTED_COLUMNS)
        return data.fillna('')
    except Exception as e:
        st.error(f"Error loading data from Database: {e}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS) # Return empty DataFrame on error
    finally:
        if conn:
            conn.close()

def load_audit_log() -> pd.DataFrame:
    """Loads data from the audit log database."""
    try:
        with sqlite3.connect(AUDIT_DB_FILE) as conn:
            query = "SELECT * FROM logs ORDER BY Timestamp DESC" # Show newest first
            data = pd.read_sql_query(query, conn)
        # Convert Timestamp back to datetime if needed for display formatting, otherwise keep as string
        # data['Timestamp'] = pd.to_datetime(data['Timestamp'])
        return data
    except Exception as e:
        st.error(f"Error loading audit log data: {e}")
        return pd.DataFrame(columns=list(AUDIT_COLUMNS_TYPES.keys()))

# --- Course Data Loading ---
def load_course_data(file_path=COURSES_FILE) -> list:
    """Loads course data from a JSON file."""
    default_courses = [
        {"name": "Default Course 1", "price": 1000.00},
        {"name": "Default Course 2", "price": 2000.00}
    ]
    try:
        if not os.path.exists(file_path):
            st.warning(f"'{file_path}' not found. Creating with default courses. Please customize it.")
            with open(file_path, 'w') as f:
                json.dump(default_courses, f, indent=2)
            return default_courses

        with open(file_path, 'r') as f:
            courses = json.load(f)
        if not isinstance(courses, list) or not all(isinstance(c, dict) and "name" in c and "price" in c for c in courses):
            st.error(f"Invalid format in '{file_path}'. Expected a list of {{'name': str, 'price': float}}.")
            return default_courses # Fallback to default
        return courses
    except Exception as e:
        st.error(f"Error loading course data from '{file_path}': {e}")
        return default_courses # Fallback to default

# --- Course Data Saving ---
def save_course_data(courses_list: list, file_path=COURSES_FILE) -> bool:
    """Saves the list of courses to the JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(courses_list, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving course data to '{file_path}': {e}")
        # Consider logging the error more formally here
        return False


# --- Student DB CRUD ---
def add_student_db(student_data: dict):
    """Adds a new student record to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cols = ', '.join([f'"{k}"' for k in student_data.keys()]) # Use quotes for column names
        placeholders = ', '.join(['?'] * len(student_data))
        sql = f"INSERT INTO students ({cols}) VALUES ({placeholders})"
        # Ensure values are in the correct order corresponding to cols
        values_tuple = tuple(student_data[k] for k in student_data.keys())
        cursor.execute(sql, values_tuple)
        conn.commit()
        log_action("ADD", record_id=student_data.get('Record ID'), details=f"Added student: {student_data.get('Student Name')}")
    except Exception as e:
        st.error(f"Error adding student to Database: {e}")
        raise # Re-raise the exception to indicate failure
    finally:
        if conn:
            conn.close()

def update_student_db(record_id: str, update_data: dict):
    """Updates an existing student record in the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        set_clause = ", ".join([f'"{k}" = ?' for k in update_data.keys()])
        sql = f'UPDATE students SET {set_clause} WHERE "Record ID" = ?'
        values = list(update_data.values()) + [record_id]
        cursor.execute(sql, values)
        conn.commit()
        # Log which fields were potentially updated
        log_action("EDIT", record_id=record_id, details=f"Updated fields: {', '.join(update_data.keys())}")
    except Exception as e:
        st.error(f"Error updating student in Database: {e}")
        raise
    finally:
        if conn:
            conn.close()

def delete_student_db(record_id: str):
    """Deletes a student record from the SQLite database."""
    with sqlite3.connect(DB_FILE) as conn: # Use context manager for auto commit/close
        cursor = conn.cursor()
        sql = 'DELETE FROM students WHERE "Record ID" = ?'
        cursor.execute(sql, (record_id,))
        log_action("DELETE", record_id=record_id, details="Deleted student record")

# --- PDF Helper Function to draw one receipt copy ---
def _draw_single_receipt_content(pdf: FPDF, details: pd.Series, y_offset: float, receipt_title: str):
    """Draws one copy of the receipt content at a given y_offset."""
    line_height = 6
    col_width_label = 45
    col_width_value = pdf.w - 2 * pdf.l_margin - col_width_label - 5 # 5 for spacing

    # Set starting position for this receipt copy
    pdf.set_y(y_offset + 5) # 10mm margin from top of this section
    x_start = pdf.get_x()

    # --- Outer Border for this receipt copy ---
    # Calculate height needed for this section (approximate, adjust as needed)
    # This is a rough estimate; dynamic height calculation can be complex.
    # For fixed content like this, a pre-calculated or trial-and-error height is often used.
    receipt_section_height = 130 # Adjusted height to properly fit all content including signatures
    pdf.rect(x_start, y_offset + 5, pdf.w - 2 * pdf.l_margin, receipt_section_height)

    # --- Header ---
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "Fee Receipt", ln=True, align='C', border=0)
    pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(0, 5, receipt_title, ln=True, align='C', border=0)
    pdf.ln(1)

    # --- Institute Details ---
    current_x = pdf.get_x() # Save current X to reset after multi_cell
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, line_height, "Progressive Computers", ln=True, align='C', border=0)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, line_height-1, "Budhi Mai colony, Raigarh (CG)", ln=True, align='C', border=0)
    pdf.cell(0, line_height-1, "Contact: 9425252051, 7489715491", ln=True, align='C', border=0)
    pdf.ln(4)

    # --- Receipt Info ---
    pdf.set_font("Helvetica", size=9)
    pdf.cell(col_width_label, line_height, "Date:", border=0)
    pdf.cell(col_width_value, line_height, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ln=True, border=0)
    pdf.cell(col_width_label, line_height, "Record ID:", border=0)
    pdf.cell(col_width_value, line_height, str(details.get('Record ID', 'N/A')), ln=True, border=0)
    pdf.ln(3)

    # --- Student Details ---
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, line_height, "Student Details:", ln=True, border="B") # Bottom border for section
    pdf.set_font("Helvetica", size=9)
    pdf.cell(col_width_label, line_height, "Name:", border=0)
    pdf.cell(col_width_value, line_height, str(details.get('Student Name', 'N/A')), ln=True, border=0)
    pdf.cell(col_width_label, line_height, "Course:", border=0)
    pdf.cell(col_width_value, line_height, str(details.get('Course Name', 'N/A')), ln=True, border=0)
    pdf.cell(col_width_label, line_height, "Enrolled On:", border=0)
    pdf.cell(col_width_value, line_height, str(details.get('Course Enrollment Date', 'N/A')), ln=True, border=0)
    pdf.cell(col_width_label, line_height, "Mobile No:", border=0)
    pdf.cell(col_width_value, line_height, str(details.get('Mobile No', 'N/A')), ln=True, border=0)
    # pdf.cell(col_width_label, line_height, "Email:", border=0) # Optional
    # pdf.cell(col_width_value, line_height, str(details.get('Email Address', 'N/A')), ln=True, border=0) # Optional
    pdf.ln(3)

    # --- Fee Details ---
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, line_height, "Fee Details:", ln=True, border="B")
    pdf.set_font("Helvetica", size=9)
    pdf.cell(col_width_label, line_height, "Total Course Fees:", border=0)
    pdf.cell(col_width_value, line_height, f"{details.get('Total Fees', 0.0):.2f}", ln=True, border=0, align='R')
    pdf.cell(col_width_label, line_height, "Total Fees Paid:", border=0)
    pdf.cell(col_width_value, line_height, f"{details.get('Fees Paid', 0.0):.2f}", ln=True, border=0, align='R')
    pdf.set_font("Helvetica", 'B', 9) # Bold for Balance
    pdf.cell(col_width_label, line_height, "Balance Fees:", border=0)
    pdf.cell(col_width_value, line_height, f"{details.get('Balance Fees', 0.0):.2f}", ln=True, border=0, align='R')
    pdf.set_font("Helvetica", size=9)
    pdf.cell(col_width_label, line_height, "Last Payment Mode:", border=0)
    pdf.cell(col_width_value, line_height, str(details.get('Fees Detail', 'N/A')), ln=True, border=0)
    pdf.ln(5)

    # --- Signature Placeholders ---
    pdf.set_y(y_offset + receipt_section_height - 20) # Position signatures near bottom of this section
    pdf.set_font("Helvetica", size=8)
    pdf.cell( (pdf.w - 2 * pdf.l_margin) / 2, line_height, "_________________________      ", ln=False, border=0, align='L')
    pdf.cell( (pdf.w - 2 * pdf.l_margin) / 2, line_height, "_________________________      ", ln=True, border=0, align='L')
    pdf.cell( (pdf.w - 2 * pdf.l_margin) / 2, line_height, "(Student Signature)", ln=False, border=0, align='C')
    pdf.cell( (pdf.w - 2 * pdf.l_margin) / 2, line_height, "(Authorized Signatory)", ln=True, border=0, align='C')
    pdf.ln(2)

    # --- Footer for this copy ---
    pdf.set_font("Helvetica", 'I', 7)
    pdf.cell(0, line_height-2, "*This is a system-generated receipt.*", ln=True, align='C', border=0)

# --- PDF Generation ---
def generate_receipt_pdf(details: pd.Series) -> bytes:
    """Generates a PDF receipt for the given student details."""
    pdf = FPDF()
    pdf.add_page()
    page_height = pdf.h
    middle_of_page = page_height / 2

    # Draw Student Copy (Top Half)
    _draw_single_receipt_content(pdf, details, y_offset=0, receipt_title="Student Copy")

    # Draw a line to separate the two halves
    pdf.set_line_width(0.5)
    pdf.set_draw_color(0, 0, 0) # Black
    # Adjust y for the line to be slightly above the start of the second receipt's border
    line_y_position = middle_of_page - 2.5 # Small offset before the next receipt's top border
    pdf.line(pdf.l_margin, line_y_position, pdf.w - pdf.r_margin, line_y_position)

    # Draw Institute Copy (Bottom Half)
    _draw_single_receipt_content(pdf, details, y_offset=middle_of_page, receipt_title="Institute Copy")

    # Output PDF as bytes
    return bytes(pdf.output(dest='S')) # Explicitly convert to bytes

# --- Admin Portal Function ---
def admin_portal():
    st.subheader("🔑 Admin Portal")
    admin_tab_audit, admin_tab_backup, admin_tab_courses = st.tabs(["📜 Audit Log", "💾 Backup/Restore", "📚 Manage Courses"])

    # --- Audit Log Tab ---
    with admin_tab_audit:
        st.header("Audit Log Viewer")
        audit_df = load_audit_log()
        if not audit_df.empty:
            st.dataframe(audit_df, use_container_width=True, hide_index=True)
        else:
            st.info("Audit log is empty.")

    # --- Backup/Restore Tab ---
    with admin_tab_backup:
        st.header("Backup Management")
        st.info("Backup functionality (e.g., manual backup trigger, restore options) can be added here.")
        # Example: Button to trigger manual backup
        if st.button("Trigger Manual Backup Now"):
            st.info("Attempting to create backups...")
            backup_database(DB_FILE, "students", BACKUP_DIR)
            backup_database(AUDIT_DB_FILE, "logs", BACKUP_DIR)
            st.success("Manual backup process initiated. Check sidebar for status.")

    # --- Manage Courses Tab ---
    with admin_tab_courses:
        st.header("Manage Courses")
        st.markdown("""
            Here you can add, edit, or delete courses.
            - To **add** a new course, scroll to the bottom of the table and fill in a new row.
            - To **edit** a course, click on the cell you want to change and type.
            - To **delete** a course, select the row(s) and press the `Delete` or `Backspace` key.
            Click **'Save Course Changes'** to apply your modifications.
        """)

        if 'course_list' in st.session_state:
            current_courses_df = pd.DataFrame(st.session_state.course_list)
        else:
            current_courses_df = pd.DataFrame(columns=['name', 'price'])

        if current_courses_df.empty or 'name' not in current_courses_df.columns or 'price' not in current_courses_df.columns:
             current_courses_df = pd.DataFrame(st.session_state.course_list if 'course_list' in st.session_state and st.session_state.course_list else [], columns=['name', 'price'])

        edited_df_from_editor = st.data_editor(
            current_courses_df,
            num_rows="dynamic",
            key="course_data_editor_widget",
            column_config={
                "name": st.column_config.TextColumn("Course Name", required=True, help="Name of the course. Must be unique."),
                "price": st.column_config.NumberColumn("Price (INR)", required=True, min_value=0.0, format="%.2f", help="Price of the course.")
            },
            use_container_width=True
        )

        if st.button("Save Course Changes", key="save_courses_button_admin"):
            valid_courses_from_editor = []
            is_data_valid = True
            processed_df = edited_df_from_editor.dropna(subset=['name'])
            processed_df = processed_df[processed_df['name'].astype(str).str.strip() != '']
            temp_course_names = []

            for index, row in processed_df.iterrows():
                name = str(row.get('name', '')).strip()
                price = row.get('price')
                if not name or name in temp_course_names:
                    st.error(f"Course name '{name}' is invalid (empty or duplicate). Please ensure all course names are unique and not empty.")
                    is_data_valid = False; break
                temp_course_names.append(name)
                if pd.isna(price) or not isinstance(price, (int, float)) or float(price) < 0:
                    st.error(f"Course '{name}': Price must be a non-negative number.")
                    is_data_valid = False; break
                valid_courses_from_editor.append({"name": name, "price": float(price)})

            if is_data_valid:
                if save_course_data(valid_courses_from_editor):
                    st.session_state.course_list = valid_courses_from_editor
                    st.session_state.course_price_map = {course['name']: course['price'] for course in st.session_state.course_list}
                    st.success("Courses updated successfully! The changes are now live.")
                    st.rerun()
# --- App Execution ---

if not check_password():
    st.stop()  # Do not continue if password is not correct.

# --- Proceed only if password is correct ---

# Set Page Config FIRST
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

# --- Backup Function ---
def backup_database(db_path, table_name, backup_dir):
    """Creates a CSV backup of a table from an SQLite database."""
    today_str = datetime.now().strftime('%Y%m%d')
    backup_file = os.path.join(backup_dir, f"{os.path.splitext(os.path.basename(db_path))[0]}_{table_name}_backup_{today_str}.csv")

    # Check if backup for today already exists
    if os.path.exists(backup_file):
        # st.sidebar.info(f"Backup for {os.path.basename(db_path)} ({table_name}) already exists for today.")
        return

    try:
        with sqlite3.connect(db_path) as conn:
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql_query(query, conn)

        if not df.empty:
            os.makedirs(backup_dir, exist_ok=True) # Create backup directory if it doesn't exist
            df.to_csv(backup_file, index=False)
            st.sidebar.success(f"Backup created: {os.path.basename(backup_file)}")
        else:
            st.sidebar.warning(f"No data found in {table_name} table of {os.path.basename(db_path)} to back up.")

    except Exception as e:
        st.sidebar.error(f"Error creating backup for {os.path.basename(db_path)} ({table_name}): {e}")

# --- Initialize Databases (after password check) ---
try:
    init_db() # Ensure DB and table exist on startup (and potentially add new column)
    init_audit_db() # Ensure Audit Log DB and table exist
except Exception as e:
    st.error(f"An error occurred during Database initialization: {e}")
    st.stop() # Stop if DBs can't be initialized

# --- Create Daily Backups (after password check and DB init) ---
backup_database(DB_FILE, "students", BACKUP_DIR)
backup_database(AUDIT_DB_FILE, "logs", BACKUP_DIR)

# Load data initially
if 'student_data' not in st.session_state:
    st.session_state.student_data = load_data()
if 'course_list' not in st.session_state:
    st.session_state.course_list = load_course_data()
    # Create a mapping for quick price lookup
    st.session_state.course_price_map = {course['name']: course['price'] for course in st.session_state.course_list}

# Use tabs for different sections
tab_view, tab_add, tab_edit_delete, tab_receipt, tab_balance = st.tabs([
    "📊 View All",
    "➕ Add Student",
    "✏️ Edit / Delete",
    "🧾 Print Receipt",
    "💰 Balance Fees"
])

# --- Admin Panel Access ---
st.sidebar.title("Admin Access")
password_attempt = st.sidebar.text_input("Enter Admin Password", type="password", key="admin_pw")
show_admin_panel = False
if password_attempt:
    if password_attempt == ADMIN_PASSWORD:
        show_admin_panel = True
        st.sidebar.success("Access Granted")
    else:
        st.sidebar.error("Incorrect Password")

# Main App Title (after potential sidebar elements)
st.title(f"{APP_ICON} {APP_TITLE}")
# --- View Students Tab ---
# --- View Students Tab ---
with tab_view:
    st.header("All Student Records")
    if not st.session_state.student_data.empty:
        # Display all columns defined in EXPECTED_COLUMNS
        # load_data ensures all these columns exist in the DataFrame
        st.dataframe(st.session_state.student_data[EXPECTED_COLUMNS], use_container_width=True, hide_index=True)
    else:
        st.info("No student data found. Add students using the 'Add Student' tab.")

    if st.button("🔄 Refresh Data from Database"):
        st.session_state.student_data = load_data()
        st.rerun()


# --- Add Student Tab ---
with tab_add:
    st.header("Add New Student Record")

    # --- Course Selection and Dependent Fields (Outside Form) ---
    st.subheader("1. Select Course")
    course_names = [course['name'] for course in st.session_state.course_list]

    def update_fees_and_date_callback(): # Renamed for clarity
        selected_course_name = st.session_state.get("add_course_select_main") # Use new key
        if selected_course_name and selected_course_name in st.session_state.course_price_map:
            st.session_state.add_total_fees_val = st.session_state.course_price_map[selected_course_name]
            st.session_state.add_enroll_date_val = datetime.now().date()
        else: # Handle case where no course is selected or selection is cleared
            st.session_state.add_total_fees_val = 0.0
            st.session_state.add_enroll_date_val = datetime.now().date()

    selected_course_main = st.selectbox("Course Name*", options=course_names, index=None, placeholder="Select a course...", key="add_course_select_main", on_change=update_fees_and_date_callback)

    with st.form("add_student_form", clear_on_submit=True):
        st.subheader("Student Details")
        s_name = st.text_input("Student Name*", key="add_s_name")
        f_name = st.text_input("Father Name", key="add_f_name")
        m_name = st.text_input("Mother Name", key="add_m_name")
        dob = st.date_input(
            "Date of Birth",
            key="add_dob",
            value=None,
            min_value=date(1950, 1, 1), # Set minimum allowed date
            max_value=datetime.now().date(), # Set maximum allowed date to today
            format="YYYY-MM-DD")
        enroll_date = st.date_input(
            "Course Enrollment Date*",
            key="add_enroll_date",
            value=st.session_state.get("add_enroll_date_val", datetime.now().date()), # Value from session state
            format="YYYY-MM-DD")
        enroll_no = st.text_input("Enrollment No (Optional)", key="add_enroll_no")
        address = st.text_area("Address", key="add_address")

        st.subheader("Contact Information")
        mobile = st.text_input("Mobile No*", key="add_mobile")
        email = st.text_input("Email Address", key="add_email")
        aadhar = st.text_input("Aadhar Card No", key="add_aadhar") # Keep as text for flexibility
        
        st.subheader("Fees Information")
        # Display selected course (read-only or just for info)
        st.markdown(f"**Selected Course:** {st.session_state.get('add_course_select_main', 'None')}")
        
        fees_detail = st.selectbox("Fees Payment Mode", ["Online", "Cheque", "Cash", "Other"], key="add_fees_detail", index=None, placeholder="Select payment mode...")
        # Total fees is now driven by session state, updated by the selectbox outside the form
        total_fees_val_form = st.number_input("Total Course Fees*", min_value=0.0, step=100.0, key="add_total_fees_val_form", value=st.session_state.get("add_total_fees_val", 0.0))
        fees_paid_val = st.number_input("Fees Paid Initially*", min_value=0.0, step=100.0, key="add_fees_paid_val", value=0.0) # Default to 0

        submitted = st.form_submit_button("➕ Add Student")


        if submitted:
            # Basic Validation
            if not s_name or not mobile or not selected_course or total_fees_val is None or fees_paid_val is None or not enroll_date:
                st.warning("Please fill in all required fields marked with *.")
            elif fees_paid > total_fees:
                 st.warning("Fees Paid cannot be greater than Total Fees.")
            elif not st.session_state.get("add_course_select_main"): # Ensure course was selected outside
                st.warning("Please select a course first.")
            else:
                try:
                    # Prepare new record
                    record_id = str(uuid.uuid4()) # Generate a unique ID
                    balance = st.session_state.get("add_total_fees_val", 0.0) - fees_paid_val # Use session state for total_fees
                    new_student_dict = {
                        'Record ID': record_id,
                        'Student Name': s_name,
                        'Father Name': f_name,
                        'Mother Name': m_name,
                        'Course Name': st.session_state.get("add_course_select_main"), # Get from session state
                        'Fees Detail': fees_detail if fees_detail else '',
                        'Date of Birth': dob.strftime('%Y-%m-%d') if dob else None, # Format as string for DB
                        'Course Enrollment Date': enroll_date.strftime('%Y-%m-%d') if enroll_date else None, # Format as string
                        'Enrollment No': enroll_no if enroll_no else None,
                        'Address': address,
                        'Aadhar Card No': aadhar,
                        'Mobile No': mobile,
                        'Email Address': email,
                        'Total Fees': st.session_state.get("add_total_fees_val", 0.0), # Get from session state
                        'Fees Paid': fees_paid_val,
                        'Balance Fees': balance
                    }

                    # Add to database
                    add_student_db(new_student_dict)

                    # Reload data into session state
                    st.session_state.student_data = load_data()

                    st.success(f"Student '{s_name}' added successfully with Record ID: {record_id}!")
                    # Clear form values from session state after successful submission
                    st.session_state.add_total_fees_val = 0.0
                    st.session_state.add_enroll_date_val = datetime.now().date()
                    st.session_state.add_fees_paid_val = 0.0
                    st.session_state.add_course_select_main = None # Reset selected course

                    # No need to clear form manually due to clear_on_submit=True

                except Exception as e:
                    st.error(f"An error occurred while adding the student: {e}")


# --- Edit / Delete Tab ---
with tab_edit_delete:
    st.header("Edit or Delete Student Record")

    if st.session_state.student_data.empty:
        st.info("No student data available to edit or delete.")
    else:
        # Create a list of options for the selectbox: "Record ID - Student Name"
        student_options = [
            f"{row['Record ID']} - {row['Student Name']}"
            for index, row in st.session_state.student_data.iterrows()
        ]
        selected_option = st.selectbox(
            "Select Student (Record ID - Name)",
            options=student_options,
            index=None, # Default to no selection
            placeholder="Choose a student to edit or delete..."
        )

        if selected_option:
            # Extract Record ID from the selected option string
            selected_record_id = selected_option.split(" - ")[0]
            student_index = st.session_state.student_data[st.session_state.student_data['Record ID'] == selected_record_id].index

            if not student_index.empty:
                student_index = student_index[0] # Get the first (and should be only) index
                student_details = st.session_state.student_data.loc[student_index].copy() # Get a copy to edit

                st.subheader(f"Editing Record ID: {selected_record_id}")

                with st.form("edit_student_form"):
                    # Display fields for editing - pre-fill with existing data
                    edit_s_name = st.text_input("Student Name*", value=student_details.get('Student Name', ''))
                    edit_f_name = st.text_input("Father Name", value=student_details.get('Father Name', ''))
                    edit_m_name = st.text_input("Mother Name", value=student_details.get('Mother Name', ''))

                    # Handle date conversion for date_input
                    current_dob = student_details.get('Date of Birth')
                    if pd.isna(current_dob) or current_dob == '':
                        edit_dob_value = None
                    elif isinstance(current_dob, str):
                         try:
                             edit_dob_value = datetime.strptime(current_dob, '%Y-%m-%d').date()
                         except ValueError:
                             edit_dob_value = None # Handle invalid date string format
                    elif isinstance(current_dob, (datetime, pd.Timestamp)):
                         edit_dob_value = current_dob.date()
                    else:
                        edit_dob_value = current_dob # Assume it's already a date object or None

                    edit_dob = st.date_input(
                        "Date of Birth",
                        value=edit_dob_value,
                        min_value=date(1950, 1, 1), # Set minimum allowed date
                        max_value=datetime.now().date(), # Set maximum allowed date to today
                        format="YYYY-MM-DD",
                        key=f"edit_dob_{selected_record_id}") # Add unique key for edit form

                    # Handle enrollment date conversion
                    current_enroll_date = student_details.get('Course Enrollment Date')
                    if pd.isna(current_enroll_date) or current_enroll_date == '':
                        edit_enroll_date_value = None
                    elif isinstance(current_enroll_date, str):
                        try:
                            edit_enroll_date_value = datetime.strptime(current_enroll_date, '%Y-%m-%d').date()
                        except ValueError:
                            edit_enroll_date_value = None
                    elif isinstance(current_enroll_date, (datetime, pd.Timestamp)):
                        edit_enroll_date_value = current_enroll_date.date()
                    else:
                        edit_enroll_date_value = current_enroll_date

                    edit_enroll_date = st.date_input(
                        "Course Enrollment Date*", value=edit_enroll_date_value,
                        format="YYYY-MM-DD", key=f"edit_enroll_{selected_record_id}")
                    edit_enroll_no = st.text_input("Enrollment No (Optional)", value=student_details.get('Enrollment No', ''))

                    edit_address = st.text_area("Address", value=student_details.get('Address', ''))
                    edit_mobile = st.text_input("Mobile No*", value=student_details.get('Mobile No', ''))
                    edit_email = st.text_input("Email Address", value=student_details.get('Email Address', ''))
                    edit_aadhar = st.text_input("Aadhar Card No", value=student_details.get('Aadhar Card No', ''))
                    edit_course = st.text_input("Course Name*", value=student_details.get('Course Name', ''))
                    edit_fees_detail = st.selectbox("Fees Payment Mode", ["Online", "Cheque", "Cash", "Other"], index=["Online", "Cheque", "Cash", "Other"].index(student_details.get('Fees Detail', 'Online')) if student_details.get('Fees Detail') in ["Online", "Cheque", "Cash", "Other"] else 0)
                    edit_total_fees = st.number_input("Total Course Fees*", min_value=0.0, step=100.0, value=float(student_details.get('Total Fees', 0.0)))
                    edit_fees_paid = st.number_input("Fees Paid*", min_value=0.0, step=100.0, value=float(student_details.get('Fees Paid', 0.0)))

                    col_save, col_delete = st.columns(2)

                    with col_save:
                        save_changes = st.form_submit_button("💾 Save Changes")

                    with col_delete:
                        delete_student = st.form_submit_button("🗑️ Delete Student")

                    if save_changes:
                        # Basic Validation
                        if not edit_s_name or not edit_mobile or not edit_course or edit_total_fees is None or edit_fees_paid is None or not edit_enroll_date:
                             st.warning("Please fill in all required fields marked with *.")
                        elif edit_fees_paid > edit_total_fees:
                             st.warning("Fees Paid cannot be greater than Total Fees.")
                        else:
                            try:
                                # Recalculate balance
                                balance = edit_total_fees - edit_fees_paid

                                # Prepare data for update
                                update_dict = {
                                    'Student Name': edit_s_name,
                                    'Father Name': edit_f_name,
                                    'Mother Name': edit_m_name,
                                    'Date of Birth': edit_dob.strftime('%Y-%m-%d') if edit_dob else None,
                                    'Course Enrollment Date': edit_enroll_date.strftime('%Y-%m-%d') if edit_enroll_date else None,
                                    'Enrollment No': edit_enroll_no if edit_enroll_no else None,
                                    'Address': edit_address,
                                    'Mobile No': edit_mobile,
                                    'Email Address': edit_email,
                                    'Aadhar Card No': edit_aadhar,
                                    'Course Name': edit_course,
                                    'Fees Detail': edit_fees_detail,
                                    'Total Fees': edit_total_fees,
                                    'Fees Paid': edit_fees_paid,
                                    'Balance Fees': balance
                                }

                                # Update database
                                update_student_db(selected_record_id, update_dict)
                                st.session_state.student_data = load_data() # Reload data
                                st.success(f"Record ID '{selected_record_id}' updated successfully!")
                                st.rerun()

                            except Exception as e:
                                st.error(f"An error occurred while saving changes: {e}")


                    if delete_student:
                        st.warning(f"⚠️ Are you sure you want to delete student '{student_details.get('Student Name', '')}' (Record ID: {selected_record_id})? This action cannot be undone.", icon="⚠️")
                        if st.button("Yes, Delete Permanently"):
                            try:
                                # Delete from database
                                delete_student_db(selected_record_id)
                                st.session_state.student_data = load_data() # Reload data
                                st.success(f"Student '{student_details.get('Student Name', '')}' deleted successfully!")
                                # Rerun to update the view and selectbox
                                st.rerun()
                            except Exception as e:
                                st.error(f"An error occurred while deleting the student: {e}")

            else:
                st.warning("Selected student record not found. It might have been deleted.")
                # Optionally clear selection or refresh data
                # st.session_state.student_data = load_data()
                # st.rerun()

# --- Print Receipt Tab ---
with tab_receipt:
    st.header("Generate Fee Receipt")

    if st.session_state.student_data.empty:
        st.info("No student data available to generate receipts.")
    else:
        student_options_receipt = [
            f"{row['Record ID']} - {row['Student Name']}"
            for index, row in st.session_state.student_data.iterrows()
        ]
        selected_option_receipt = st.selectbox(
            "Select Student for Receipt",
            options=student_options_receipt,
            index=None,
            placeholder="Choose a student..."
        )

        if selected_option_receipt:
            selected_record_id_receipt = selected_option_receipt.split(" - ")[0]
            receipt_student_details = st.session_state.student_data[st.session_state.student_data['Record ID'] == selected_record_id_receipt]

            if not receipt_student_details.empty:
                details = receipt_student_details.iloc[0] # Get the Series

                st.subheader(f"Receipt for: {details['Student Name']}")

                # --- Display Receipt Details in Markdown ---
                st.markdown("---") # Add a separator
                st.markdown(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                st.markdown("#### Student Details:")
                st.markdown(f"*   **Record ID:** {details.get('Record ID', 'N/A')}")
                st.markdown(f"*   **Name:** {details.get('Student Name', 'N/A')}")
                st.markdown(f"*   **Course:** {details.get('Course Name', 'N/A')}")
                st.markdown(f"*   **Enrolled On:** {details.get('Course Enrollment Date', 'N/A')}")
                st.markdown(f"*   **Mobile No:** {details.get('Mobile No', 'N/A')}")
                st.markdown(f"*   **Email:** {details.get('Email Address', 'N/A')}")

                st.markdown("#### Fee Details:")
                st.markdown(f"*   **Total Course Fees:** {details.get('Total Fees', 0.0):.2f}")
                st.markdown(f"*   **Total Fees Paid:** {details.get('Fees Paid', 0.0):.2f}")
                st.markdown(f"*   **Balance Fees:** {details.get('Balance Fees', 0.0):.2f}")
                st.markdown(f"*   **Last Payment Mode:** {details.get('Fees Detail', 'N/A')}")

                st.markdown("#### Institute Details:")
                st.markdown("*    Progressive Computers")
                st.markdown("*    Budhi Mai colony, Raigarh (CG)")
                st.markdown("*    9425252051, 7489715491")
                st.markdown("---")
                st.caption("*This is a system-generated receipt.*")
                st.markdown("---") # Add another separator

                # --- PDF Download Button ---
                try:
                    # Generate PDF bytes
                    pdf_bytes = generate_receipt_pdf(details) # Assuming generate_receipt_pdf exists

                    # Create filename
                    pdf_filename = f"Receipt_{details.get('Student Name', 'Unknown').replace(' ', '_')}_{details.get('Record ID', 'N_A')}.pdf"

                    # Add download button
                    st.download_button(
                        label="📄 Download Receipt PDF",
                        data=pdf_bytes,
                        file_name=pdf_filename,
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(f"An error occurred while generating the PDF: {e}")

            else:
                st.warning("Selected student record not found.")

# --- Balance Fees Tab ---
with tab_balance:
    st.header("Students with Outstanding Balance")

    if not st.session_state.student_data.empty:
        # Ensure Balance Fees is numeric for filtering
        st.session_state.student_data['Balance Fees'] = pd.to_numeric(st.session_state.student_data['Balance Fees'], errors='coerce').fillna(0)

        # Filter students with balance > 0
        balance_df = st.session_state.student_data[st.session_state.student_data['Balance Fees'] > 0]

        if not balance_df.empty:
            st.warning(f"Found {len(balance_df)} student(s) with pending fees.")
            # Define desired columns for the balance view
            balance_view_cols = [
                'Record ID', 'Student Name', 'Course Name', 'Course Enrollment Date',
                'Mobile No', 'Total Fees', 'Fees Paid', 'Balance Fees'
            ]
            # Filter the DataFrame to show only existing columns from the desired list
            existing_balance_cols = [col for col in balance_view_cols if col in balance_df.columns]
            st.dataframe(
                balance_df[existing_balance_cols],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("All students have cleared their dues!")
    else:
        st.info("No student data available.")

# --- Admin Panel Tab (Conditionally Displayed) ---
# The admin_portal function will be called here, which contains its own tabs.
if show_admin_panel:
    admin_portal() # Call the admin portal function

# --- Footer ---
st.markdown("---")
st.caption("Built with Streamlit & SQLite")
