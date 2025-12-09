import sqlite3
import re
import os
from google import genai
from google.genai.errors import APIError

# --- 1. CONFIGURATION ---
# IMPORTANT: Replace with your actual API key or ensure it's set in your environment variables
# You can get a key from Google AI Studio.
try:
    # Uses the GEMINI_API_KEY environment variable by default
    client = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    print("Please ensure your GEMINI_API_KEY environment variable is set correctly.")
    exit()

# Model for code generation
MODEL_NAME = "gemini-2.5-flash" 

# --- 2. AGENT CLASS ---

class SqliteAgent:
    """
    A custom agent that translates natural language into restricted SQL
    (SELECT and schema inspection only) for a SQLite database.
    """

    def __init__(self, db_path=":memory:", table_names=None):
        """
        Initializes the database connection and prepares the tables.
        
        :param db_path: Path to the SQLite database file. Default is in-memory.
        :param table_names: A list of table names to use for schema description.
        """
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.table_names = table_names if table_names is not None else []
        self._setup_database()
        print(f"Agent initialized and connected to database: {db_path}")

    def _setup_database(self):
        """Creates example tables for demonstration."""
        print("Creating example tables...")
        
        # Table 1: Employees
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Employees (
                employee_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT,
                salary REAL
            );
        """)
        self.cursor.executemany("INSERT INTO Employees VALUES (?, ?, ?, ?)", [
            (101, 'Alice Smith', 'Sales', 60000.00),
            (102, 'Bob Johnson', 'IT', 75000.00),
            (103, 'Charlie Brown', 'Sales', 62000.00),
            (104, 'Diana Prince', 'HR', 55000.00),
            (105, 'Clark Kent', 'IT', 80000.00)
        ])
        
        # Table 2: Departments
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Departments (
                dept_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
        """)
        self.cursor.executemany("INSERT INTO Departments VALUES (?, ?)", [
            (1, 'Sales'),
            (2, 'IT'),
            (3, 'HR')
        ])
        
        self.conn.commit()
        
        # Update table names for schema description
        self.table_names = ['Employees', 'Departments']

    def _get_schema_description(self):
        """Generates the schema for the prompt to guide the LLM."""
        schema_parts = []
        for table in self.table_names:
            # PRAGMA table_info(table) returns schema details
            self.cursor.execute(f"PRAGMA table_info({table})")
            columns = [f"{col[1]} ({col[2]})" for col in self.cursor.fetchall()]
            schema_parts.append(f"Table **{table}**: ({', '.join(columns)})")
        
        return "\n".join(schema_parts)

    def _generate_sql(self, user_prompt: str) -> str:
        """Uses the Gemini API to generate the restricted SQL query."""
        schema = self._get_schema_description()
        
        # The prompt is based on the ReACT constraints from the previous response
        # but formatted for a single call for code generation.
        system_prompt = f"""
        You are a View-Only SQL Generator. Your task is to translate the user's request into a single, valid SQLite SQL query.

        **CURRENT DATABASE SCHEMA:**
        {schema}

        **STRICT RULES:**
        1.  **ONLY SELECT/DESCRIBE:** Your output MUST ONLY be a valid `SELECT` statement or a SQLite `PRAGMA table_info(<table_name>)` statement (which serves as the 'DESCRIBE TABLE' equivalent).
        2.  **REJECT DML/DDL:** You MUST reject and refuse to generate any query that is NOT `SELECT` or `PRAGMA table_info`. This includes INSERT, UPDATE, DELETE, DROP, ALTER, etc.
        3.  **LIMIT 100:** All `SELECT` queries MUST include `LIMIT 100` at the end.
        4.  **OUTPUT FORMAT:** Respond ONLY with the SQL query text. Do not include any explanations, Markdown formatting (e.g., ```sql`), or extra text.
        """
        
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[user_prompt],
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    # Setting a high temperature for potentially complex SQL generation
                    temperature=0.4, 
                )
            )
            return response.text.strip()
        except APIError as e:
            print(f"Gemini API Error: {e}")
            return f"ERROR: Could not generate SQL due to API issue: {e}"

    def execute_prompt(self, user_prompt: str):
        """Processes the user prompt, generates SQL, validates, and executes."""
        print(f"\n--- USER PROMPT: '{user_prompt}' ---")
        
        # 1. Generate SQL from NL
        generated_sql = self._generate_sql(user_prompt)
        print(f"Generated SQL: {generated_sql}")

        # 2. Validation (The Critical Security Layer)
        normalized_sql = generated_sql.upper().strip()
        
        # Regex to check for allowed commands at the start of the query
        allowed_pattern = re.compile(r"^(SELECT|PRAGMA TABLE_INFO|PRAGMA table_info)", re.IGNORECASE)
        
        if not allowed_pattern.match(normalized_sql):
            print("\n❌ VALIDATION REJECTED: Only SELECT and PRAGMA table_info statements are allowed.")
            return "Query rejected. This agent is restricted to SELECT and DESCRIBE TABLE operations only."

        # 3. Final Execution
        try:
            self.cursor.execute(generated_sql)
            
            # Check if it was a PRAGMA (DESCRIBE) or a SELECT
            if normalized_sql.startswith("PRAGMA"):
                header = [desc[0] for desc in self.cursor.description]
                results = self.cursor.fetchall()
                print("✅ Execution Success (Schema Description):")
                print(f"Header: {header}")
                print(f"Results (first 5 rows): {results[:5]}")
                return results

            else: # Must be SELECT
                header = [desc[0] for desc in self.cursor.description]
                results = self.cursor.fetchall()
                print(f"✅ Execution Success (SELECT, {len(results)} rows returned):")
                
                # Format the results nicely
                if not results:
                    return "No results found for your query."

                # Simple output formatting for console
                output = [" | ".join(header)]
                output.append("-" * len(output[0]))
                for row in results:
                    output.append(" | ".join(map(str, row)))

                return "\n".join(output)

        except sqlite3.Error as e:
            print(f"\n❌ SQL Execution Error: {e}")
            return f"Error executing SQL: {e}"

# --- 3. EXECUTION DEMO ---

if __name__ == "__main__":
    # Create the agent (database is in-memory for the demo)
    agent = SqliteAgent()

    print("\n" + "="*50)
    print("🤖 Agent Demonstration: Allowed Queries")
    print("="*50)

    # 1. Allowed: Simple SELECT with mandatory LIMIT 100
    allowed_1 = "Show me the name and salary of the highest-paid employee."
    agent.execute_prompt(allowed_1)

    # 2. Allowed: DESCRIBE TABLE (schema inspection)
    allowed_2 = "What are the columns in the Departments table?"
    agent.execute_prompt(allowed_2)
    
    # 3. Allowed: SELECT with join, still restricted
    allowed_3 = "Find all employees who work in the 'IT' department and list their names."
    agent.execute_prompt(allowed_3)

    print("\n" + "="*50)
    print("🚫 Agent Demonstration: Rejected Queries")
    print("="*50)
    
    # 4. Rejected: DML attempt
    rejected_1 = "Change the salary of Alice Smith to 90000."
    agent.execute_prompt(rejected_1)

    # 5. Rejected: DDL attempt
    rejected_2 = "Create a new table called Projects."
    agent.execute_prompt(rejected_2)
    
    # 6. Rejected: DELETE attempt
    rejected_3 = "Delete all employees in the HR department."
    agent.execute_prompt(rejected_3)
