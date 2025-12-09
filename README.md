# vizuara-agents by AAMOD SARDESHPANDE
agentic library coded from scratch to perform safe(read only)  
![SAMPLE RUN](img.png)

# READ ME + FINAL REPORT 
Code (single small package or single file): Agent class, tools, prompts, and utilities;  
1. db.py : to check the sample db , first run db.py to populate the database and sample
2. sample.py : 
to check how the agent is using the react template run , here only the react thought process is highlighted to avoid too much smudging 3.main.py : to actually run the project with complete error tracing and REACT chain
within 350–400 LOC (excl. comments/docstrings).  
B. README (1 page): Purpose, how to run, tool list (arguments & returns), and a short  
example run with trace.  
C. Tests (3–5): Please find the tests in /tests folder
D. Trace Logs: please find this in /TraceLogs simple.log: simplified logs with only REACT Loop shown  
actual.log: shows complete set up and run logs with debug errorsas well  
E. Reflection (≤ 300 words): Please find this in the report section of this README  
# REPORT 

1. Research Evolution  
1.1 Initial Approach: Single-File Prompt  
Problem Encountered:  

Initially used a single prompt.txt file containing all instructions

Key Issue: Failed to maintain inter-stage context in the ReACT loop

Each stage lost visibility into previous reasoning steps

Contextual flow between Reason→Think→Action stages was broken 
```prompt.txt
You are a View-Only SQL Agent. Your sole purpose is to generate safe, read-only SQL queries (SELECT statements) to fulfill user requests.

**I. STRICT CONSTRAINTS:**
1.  **READ-ONLY ONLY:** The query MUST begin with `SELECT`. Non-SELECT statements (INSERT, UPDATE, DELETE, DROP, etc.) are **STRICTLY FORBIDDEN**.
2.  **WHELISTED IDENTIFIERS:** You MUST ONLY use table and column names that are explicitly provided in the database schema context.
3.  **MANDATORY LIMIT:** The query MUST end with `LIMIT 100`.
4.  **JOIN LIMITS:** If a join is necessary, you are limited to a single `INNER JOIN` only.
5.  **ALLOWED CLAUSES:** `FROM`, `WHERE`, `GROUP BY`, `ORDER BY`, `LIMIT`.

**II. AVAILABLE TOOL:**
* `sql_query`: Takes a valid SQL SELECT string as input. Returns the query result or an error.

**III. ReACT INSTRUCTION SCHEMA:**
Your response MUST follow the Thought/Action/Observation/Answer format.

Thought
I must analyze the user request, map it to the provided schema, enforce all constraints (especially LIMIT 100), and construct the query.
Action: sql_query[<your-validated-sql-select-statement>]
Observation: <query-result-or-error>
... (Continue until a final answer can be formulated)
Answer: <final-natural-language-answer-based-on-sql-results>
```

1.2 Improved Approach: Stage-Specific Prompts  
Solution Implemented:  

Hardcoded specific prompts within each individual stage of the ReACT loop

Pass output from one stage as context to the next stage

Maintains clear separation of concerns between stages

Preserves contextual information throughout the agent's decision-making process for example

```python 
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
```

2. #### SqliteAgent Class  

The main agent class implementing the ReACT loop with the following responsibilities:  

- Database connection management  
    
- Schema extraction and description  
    
- ReACT loop orchestration  
    
- Query validation and execution  

## Tradeoffs  
I chose hardcoded prompts over external configuration files to ensure tight integration between ReACT stages, accepting reduced customization flexibility for better context preservation.   

For security, we implemented lightweight regex validation instead of full SQL parsing, trading comprehensive protection against complex injection attacks for minimal dependencies and faster execution.  Another thing i implemented is to ask llm to check whether it is movfing the table and if it is then halt immediatelyboth work satisfoctorily.  

 implicit context passing through prompt composition rather than explicit data structures, gaining simpler code flow at the cost of less control over intermediate representation.  

## Future Considerations  

1. we should prioritize **enhanced security** through SQL parsing libraries like sqlparse,  
2. Extending this via Kafka( so the LLM outputs in a kafka queue and a python program executes whatever is in this queue , hence if suddenly program is aborted we can still resume from where we left out)  
3. Accomodate long term memory by allowing user to write a small text file(example.txt) that encapsulates the long term context the user wants llm to remember between calls and this can be read by the program and passed to LLM ouput in every call .  

# SET UP 
```bash
cd /vizuara-agents
pip install requirements.txt
#copy paste your api key (of gemini) and paste in env.txt file
export GEMINI_API_KEY=$(cat env.txt)
```  
# EXECUTION  
to check the sample db , first run db.py to populate the database and sample 
```bash
python3 db.py
```
to check how the agent is using the react template run , here only the react thought process is highlighted to avoid too much smudging
```bash
python3 sample.py
```
to actually run the project with complete error tracing and REACT chain
```bash
python3 main.py
```
