FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN useradd -m app && chown -R app /app
USER app
EXPOSE 5000
# One worker + threads: finished reports are kept in memory, so all requests must hit the same process.
CMD ["gunicorn", "-w", "1", "--threads", "4", "-t", "300", "-b", "0.0.0.0:5000", "app:app"]
