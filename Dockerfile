FROM registry.access.redhat.com/ubi9/python-312:latest

ENV HOME=/opt/app-root/src \
    PYTHONPATH=/opt/app-root/src \
    STREAMLIT_SERVER_PORT=8080 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    SPRINTWEAVE_DATA_DIR=/data \
    SPRINTWEAVE_PROMPTS=/opt/app-root/src/prompts

WORKDIR /opt/app-root/src

USER 0
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ui/ ./ui/
COPY api/ ./api/
COPY llm/ ./llm/
COPY prompts/ ./prompts/
RUN mkdir -p /data/jobs \
    && chgrp -R 0 /opt/app-root /data \
    && chmod -R g=u /opt/app-root /data
USER 1001

EXPOSE 8080 8000

CMD ["streamlit", "run", "ui/app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]
