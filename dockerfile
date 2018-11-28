FROM python:3.6.1

RUN apt-get update && apt-get install -y swig libasound2-dev

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD ./static static
ADD ./templates templates
ADD app.py .
ADD serials.csv .
ADD ./isobar isobar
ADD ./childrens_corner1.mid .

CMD ["python","app.py"]