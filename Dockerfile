FROM 194943407731.dkr.ecr.eu-west-1.amazonaws.com/python:latest

WORKDIR /app

COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

COPY joeBot /app/joeBot
COPY content /app/content
COPY main.py /app/

CMD ["python", "./main.py"]