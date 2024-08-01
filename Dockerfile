FROM python:3.11.7-alpine

RUN pip3 install requests && \
    rm -r /root/.cache

# Create app directory
WORKDIR /plugin.video.mlbserver

# Bundle app source
COPY . .

EXPOSE 5714
CMD [ "python3", "-u", "service.py" ]
