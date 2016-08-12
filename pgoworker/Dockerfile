FROM ubuntu:14.04
MAINTAINER Di Chen <chenditc@gmail.com>
RUN apt-get update -y && apt-get install -y libpq-dev \
                                            python-dev \
                                            ssh 

# Install Python Setuptools
RUN apt-get install -y python-setuptools

# Install pip
RUN easy_install pip

# Add and install Python modules
ADD requirements.txt /src/requirements.txt
RUN cd /src; pip install -r requirements.txt

# Bundle app source
ADD . /src
ADD ./encrypt.so /usr/local/bin/encrypt.so

# Add logging mount point

# Copy ssh key
Add ./id_rsa /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa

# Expose
EXPOSE  8080

# Run
CMD ["/src/start.sh"]
