FROM python:3.13-bookworm

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./app /app
COPY alembic.ini .
COPY ./alembic /alembic
COPY  start.sh .
ENV PYTHONPATH=/
CMD ["/bin/sh", "start.sh"]