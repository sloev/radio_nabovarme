FROM python:3.6.1

ADD requirements.txt .

RUN pip install -r requirements.txt

ADD ./static static
ADD ./templates templates
ADD app.py .
ADD serials.csv .

CMD ["python","app.py"]