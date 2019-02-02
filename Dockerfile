FROM python:3.7.2

ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
COPY ./src /code/
RUN pip install -r requirements.txt
