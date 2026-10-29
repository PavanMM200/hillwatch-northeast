FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend /app/backend
COPY scripts /app/scripts
COPY matlab /app/matlab
COPY alembic.ini /app/alembic.ini
RUN useradd -u 10001 -m hillwatch && mkdir /app/data && chown hillwatch /app/data
USER hillwatch
ENV PYTHONPATH=/app/backend
EXPOSE 8000
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
