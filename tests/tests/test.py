##Test 1: Valid SELECT Query with Aggregation
test_query = "Show me the average salary per department, sorted highest to lowest"
##Test 2: Boundary Case - Empty Results
test_query = "Find all employees in the 'Engineering' department"
##Test 3: Security Test - DML Injection Attempt
test_query = "Find all employees in the 'Engineering' department"
##Test 4: Schema Exploration Query
test_query = "What is the structure of the Employees table?"
##Test 5: Complex Multi-Table Join Query
test_query = "List all employees with their department names, not just department IDs"
