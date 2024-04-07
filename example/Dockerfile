FROM python:3.12-slim

COPY ./requirements.txt /

RUN pip install -r /requirements.txt

RUN rm -rf /requirements.txt

# makemigrations

# migrate

#infinite tail
CMD ["tail", "-f", "/dev/null"]