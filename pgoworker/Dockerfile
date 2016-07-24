FROM ubuntu:14.04
MAINTAINER Di Chen <chenditc@gmail.com>
RUN apt-get update -y && apt-get install -y libpq-dev \
                                            python-dev 

# Install Python Setuptools
RUN apt-get install -y python-setuptools

# Install pip
RUN easy_install pip

# Add and install Python modules
ADD requirements.txt /src/requirements.txt
RUN cd /src; pip install -r requirements.txt

# Bundle app source
ADD . /src

# Add logging mount point


# Expose
EXPOSE  8080

# Run
CMD ["python", "/src/manage.py", "runserver", "0.0.0.0:8080"]
