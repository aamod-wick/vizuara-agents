import sqlite3

def setup_demo_database(db_path=":memory:"):
    """
    Connects to a SQLite database and creates/populates the necessary tables 
    ('Employees' and 'Departments') for the demo.
    
    :param db_path: Path to the SQLite database file. Default is in-memory.
    :return: A sqlite3 connection object.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"Connected to database: {db_path}")

        # --- 1. Create Employees Table ---
        print("Creating Employees table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Employees (
                employee_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT,
                salary REAL
            );
        """)
        
        # --- 2. Insert Employee Data ---
        print("Inserting Employee data...")
        employee_data = [
            (101, 'Alice Smith', 'Sales', 60000.00),
            (102, 'Bob Johnson', 'IT', 75000.00),
            (103, 'Charlie Brown', 'Sales', 62000.00),
            (104, 'Diana Prince', 'HR', 55000.00),
            (105, 'Clark Kent', 'IT', 80000.00)
        ]
        cursor.executemany("INSERT INTO Employees VALUES (?, ?, ?, ?)", employee_data)
        
        # --- 3. Create Departments Table ---
        print("Creating Departments table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Departments (
                dept_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
        """)
        
        # --- 4. Insert Department Data ---
        print("Inserting Department data...")
        department_data = [
            (1, 'Sales'),
            (2, 'IT'),
            (3, 'HR')
        ]
        cursor.executemany("INSERT INTO Departments VALUES (?, ?)", department_data)
        
        # --- 5. Commit Changes ---
        conn.commit()
        print("Database setup complete.")
        
        return conn

    except sqlite3.Error as e:
        print(f"An error occurred during database setup: {e}")
        # Ensure connection is closed if an error occurs
        if 'conn' in locals() and conn:
            conn.close()
        return None

if __name__ == "__main__":
    # Example usage: setup an in-memory database for testing
    demo_conn = setup_demo_database()
    
    if demo_conn:
        # Verify data insertion (Optional)
        cursor = demo_conn.cursor()
        
        print("\n\n-----------------------------------------------------------------------THIS IS A SAMPLE DATABASE TO RUN OUR CODE AND BELOW YOU WILL GET A GLIMPSE OF OUR DATABASE-----------------------------------------------------------------------\n\n")
        cursor.execute("SELECT * FROM Employees LIMIT 5")
        employees = cursor.fetchall()
        print("\nVerification (First 5 Employees):")
        print(employees)
        print("\n\n----------------------------------------------------------------------------------------------------------------------------------------------\n\n")
        # Close the connection
        demo_conn.close()
