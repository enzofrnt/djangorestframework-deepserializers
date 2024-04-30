FROM python:3.12-slim

COPY ./requirements.txt /

RUN pip install -r /requirements.txt

RUN rm -rf /requirements.txt

WORKDIR /app

COPY ./app /app

# replace the following commend by an infinite loop to keep the container running and make modifications
CMD ["tail", "-f", "/dev/null"]
# RUN python manage.py makemigrations

# RUN python manage.py migrate

# CMD [ "python", "manage.py", "runserver", "0.0.0.0:8000" ]