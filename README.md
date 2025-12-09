# vizuara-agents
agentic library coded from scratch to perform safe(read only)  

# READ ME + FINAL REPORT 

# REPORT 


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
