FROM 194943407731.dkr.ecr.eu-west-1.amazonaws.com/python:latest

WORKDIR /app
COPY joeBot /app/joeBot
COPY content /app/content
COPY main.py /app/
COPY requirements.txt /app/

RUN pip install requirements.txt

CMD ["python", "./main.py"]