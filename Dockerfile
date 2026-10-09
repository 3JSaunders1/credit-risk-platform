# Credit Risk Platform: serves the Streamlit dashboard on port 8501
FROM python:3.11-slim-bookworm

WORKDIR /app
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
