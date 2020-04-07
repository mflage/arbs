FROM python:3.8-slim-buster
LABEL maintainer="Marius Flage <marius@flage.org>"

# the default configuration - needs to be updated
COPY requirements-news.txt /tmp/
COPY news_schema.yaml /app/
COPY grab_news.py /app/
COPY default_configuration.cfg /app/
COPY entrypoint.sh /
RUN apt-get update && apt-get install -y cron
RUN pip3 install -r /tmp/requirements-news.txt
RUN rm /tmp/requirements-news.txt
RUN chmod +x /entrypoint.sh /app/grab_news.py
ENTRYPOINT /entrypoint.sh
