FROM python:3.11-alpine

RUN pip3 install requests && \
    rm -r /root/.cache

# Create app directory
WORKDIR /plugin.video.mlb

# Bundle app source
COPY . .

EXPOSE 5714
CMD [ "python3", "service.py" ]
