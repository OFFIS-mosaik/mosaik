FROM python:3.7

WORKDIR /usr/src/app

#COPY requirements.txt ./
COPY . .
RUN pip install --upgrade pip
#RUN rm -r venv 

# install and configure virtualenv
#RUN pip install virtualenv
#RUN virtualenv venv
#RUN /bin/bash -c "source venv/bin/activate"
#RUN . venv/bin/activate && pip3 install -r /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt
#RUN python setup.py bdist_wheel sdist
RUN ls
RUN pip install .
RUN pip install tox
RUN tox -e py37
