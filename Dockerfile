FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=5000
WORKDIR /app
RUN addgroup --system --gid 10001 asda && adduser --system --uid 10001 --ingroup asda asda
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY asda ./asda
COPY migrations ./migrations
COPY wsgi.py ./wsgi.py
RUN mkdir -p /data && chown -R asda:asda /app /data
USER asda
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/healthz',timeout=3)" || exit 1
CMD ["sh", "-c", "flask --app asda.app db upgrade && exec gunicorn --bind 0.0.0.0:5000 --workers 2 --access-logfile - wsgi:app"]
