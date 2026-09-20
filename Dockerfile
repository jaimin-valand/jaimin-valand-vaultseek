FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir . && useradd --create-home --uid 10001 appuser
USER appuser
ENV PSE_ENV=production
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "from urllib.request import urlopen; urlopen(\"http://127.0.0.1:8000/health\", timeout=3).read()"
CMD ["uvicorn","private_search_engine.api.app:app","--host","0.0.0.0","--port","8000"]
