FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup --system app && adduser --system --ingroup app app
RUN mkdir /app/data && chown app:app /app/data
COPY --chown=app:app app ./app

WORKDIR /app/app
EXPOSE 5000
USER app

CMD ["sh", "-c", "python init_db.py && exec uvicorn main:app --host 0.0.0.0 --port 5000"]