FROM python:3.10-alpine

RUN mkdir /app

EXPOSE 8000

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY . /app/

CMD [ "uvicorn", "main:app" ]