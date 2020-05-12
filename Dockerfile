FROM python:3.7

WORKDIR /usr/src/app

COPY . .

RUN pip3 install -r requirements.txt

USER nobody:nogroup

CMD ["python3", "status-page.py", "configuration.json", "log.txt"]