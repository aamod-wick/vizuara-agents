import sqlite3
import re
import os
import logging
from google import genai
from google.genai.errors import APIError

# --- 1. CONFIGURATION ---

# Setup basic logging to see DEBUG and higher messages
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('SqliteAgent')

try:
    # Initialize the Gemini Client. 
    # It will automatically look for the GEMINI_API_KEY environment variable.
    client = genai.Client()
    logger.info("Gemini client initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing Gemini client. Is GEMINI_API_KEY set? Error: {e}")
    # Exit if the client can't be initialized (required for API calls)
    exit()

MODEL_NAME = "gemini-2.5-flash" 

# --- 2. AGENT CLASS ---

class SqliteAgent:
    """
    A custom agent that uses a three-stage LLM-driven ReACT loop (Reason, Think, Action)
    to generate and execute restricted SQL.
    """

    def __init__(self, db_path=":memory:", table_names=None):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.table_names = table_names if table_names is not None else []
        self.logger = logger
        self._setup_database()

    def _setup_database(self):
        """Creates example tables and populates them."""
        self.logger.info("Setting up example database tables...")
        
        # Create Tables and Insert Data
        self.cursor.execute("CREATE TABLE IF NOT EXISTS Employees (employee_id INTEGER PRIMARY KEY, name TEXT NOT NULL, department TEXT, salary REAL);")
        self.cursor.executemany("INSERT INTO Employees VALUES (?, ?, ?, ?)", [
            (101, 'Alice Smith', 'Sales', 60000.00),
            (102, 'Bob Johnson', 'IT', 75000.00),
            (103, 'Charlie Brown', 'Sales', 62000.00),
            (104, 'Diana Prince', 'HR', 55000.00),
            (105, 'Clark Kent', 'IT', 80000.00)
        ])
        self.cursor.execute("CREATE TABLE IF NOT EXISTS Departments (dept_id INTEGER PRIMARY KEY, name TEXT NOT NULL);")
        self.cursor.executemany("INSERT INTO Departments VALUES (?, ?)", [
            (1, 'Sales'),
            (2, 'IT'),
            (3, 'HR')
        ])
        
        self.conn.commit()
        self.table_names = ['Employees', 'Departments']
        self.logger.info("Database structure created and populated.")

    def _get_schema_description(self):
        """Generates the schema string for the LLM context."""
        schema_parts = []
        for table in self.table_names:
            self.cursor.execute(f"PRAGMA table_info({table})")
            columns = [f"{col[1]} ({col[2]})" for col in self.cursor.fetchall()]
            schema_parts.append(f"Table **{table}**: ({', '.join(columns)})")
        return "\n".join(schema_parts)

    def _llm_call(self, prompt: str, context: str) -> str:
        """Helper for a single, focused LLM call."""
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[context + "\n\nUser Request: " + prompt],
                config=genai.types.GenerateContentConfig(
                    # Keep temperature low for precise, instructional responses
                    temperature=0.2, 
                )
            )
            return response.text.strip()
        except APIError as e:
            self.logger.error(f"Gemini API Error: {e}")
            return "ERROR: API Call Failed"

    def execute_prompt(self, user_prompt: str):
        """Processes the user prompt using the explicit ReACT steps."""
        self.logger.info("\n" + "="*50)
        self.logger.info(f"STARTING ReACT FOR: {user_prompt}")
        self.logger.info("="*50)
        
        schema = self._get_schema_description()
        
        # --- 1. REASON (Database Knowledge/Plan) ---
        reason_context = f"""
        **ROLE:** You are the **REASON** component of an SQL agent. 
        **SCHEMA:** {schema}
        **TASK:** Explain, in a single sentence, which table(s) contain the necessary data to answer the user request.
        **OUTPUT FORMAT:** Respond ONLY with the reasoning sentence.
        """
        reason = self._llm_call(user_prompt, reason_context)
        self.logger.info(f"🧠 REASON (Database Look): {reason}")

        # --- 2. THINK (Query Logic/Plan) ---
        think_context = f"""
        **ROLE:** You are the **THINK** component of an SQL agent.
        **TASK:** Explain, in a single sentence, the logical steps required to construct the query (e.g., 'I must filter by X and order by Y'). Use the schema and the previous REASON step as context.
        **OUTPUT FORMAT:** Respond ONLY with the thinking sentence.
        """
        think = self._llm_call(user_prompt, think_context)
        self.logger.info(f"🤔 THINK (Query Logic): {think}")
        
        # --- 3. ACT (SQL Generation) ---
        sql_context = f"""
        **ROLE:** You are the **ACTION** component of an SQL agent.
        **STRICT RULES:** 1. ONLY generate a valid SELECT or PRAGMA statement. 2. REJECT DML/DDL. 3. All SELECTs MUST include LIMIT 100.
        **TASK:** Generate the final, executable, and constrained SQLite SQL query.
        **OUTPUT FORMAT:** Respond ONLY with the SQL query text.
        """
        generated_sql = self._llm_call(user_prompt, sql_context)
        self.logger.warning(f"🔨 ACT (Generated SQL): {generated_sql}")

        # --- 4. EXECUTE & OBSERVE (Validation and DB Execution) ---
        
        # Validation (Security Gate)
        normalized_sql = generated_sql.upper().strip()
        allowed_pattern = re.compile(r"^(SELECT|PRAGMA TABLE_INFO|PRAGMA table_info)", re.IGNORECASE)
        
        if not allowed_pattern.match(normalized_sql):
            self.logger.error(f"❌ EXECUTE FAILURE: Security rejection of unauthorized command: {normalized_sql.split()[0]}.")
            return "Query rejected. Agent is restricted to SELECT/DESCRIBE only."

        self.logger.debug("✅ VALIDATION SUCCESS: Query is safe. Executing...")

        try:
            self.cursor.execute(generated_sql)
            
            header = [desc[0] for desc in self.cursor.description]
            results = self.cursor.fetchall()
            
            # Log the Observation
            self.logger.info(f"📊 OBSERVATION (DB Result): Executed successfully, {len(results)} rows returned.")
            
            # Format the Answer
            if not results:
                return "No results found for your query."

            output = [f"| {' | '.join(header)} |"]
            output.append(f"|{'-' * (len(output[0]) - 2)}|")
            for row in results:
                formatted_row = []
                for item in row:
                    formatted_row.append(str(item))
                output.append(f"| {' | '.join(formatted_row)} |")

            return "\n\nFINAL ANSWER:\n" + "\n".join(output)

        except sqlite3.Error as e:
            self.logger.error(f"❌ OBSERVATION (SQL Error): {e}")
            return f"Error executing SQL: {e}"

# --- 3. EXECUTION DEMO ---

if __name__ == "__main__":
    
    # Initialize the agent
    agent = SqliteAgent()

    # --- DEMO 1: ALLOWED Query (SELECT) ---
    allowed_query = "Who is the highest paid employee and what is their salary?"
    result = agent.execute_prompt(allowed_query)
    print(result)

    # --- DEMO 2: ALLOWED Query (DESCRIBE) ---
    describe_query = "What columns are available in the Departments table?"
    result = agent.execute_prompt(describe_query)
    print(result)

    # --- DEMO 3: REJECTED Query (DML) ---
    rejected_query = "Update Bob Johnson's salary to 100000."
    result = agent.execute_prompt(rejected_query)
    print(result)
