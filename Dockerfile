FROM python:3.12-slim
WORKDIR /srv
ENV ENTORNO=produccion DB_PATH=/srv/datos/solicitudes.db PYTHONDONTWRITEBYTECODE=1
RUN useradd --create-home app && mkdir -p /srv/datos && chown app /srv/datos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
