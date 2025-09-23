import subprocess
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# sobe o streamlit em paralelo
subprocess.Popen(["streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true"])

@app.get("/")
def root():
    return HTMLResponse(
        """
        <h1>Dashboard Cliente</h1>
        <iframe src="http://localhost:8501" width="100%" height="800"></iframe>
        """
    )
