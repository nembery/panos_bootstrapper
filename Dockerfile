
FROM python:alpine

LABEL description="Panos Bootstrap Builder Tool"
LABEL version="0.1"
LABEL maintainer="nembery@paloaltonetworks.com"

WORKDIR /app
ADD requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY bootstrapper /app/bootstrapper
COPY tests /app/tests

EXPOSE 5000

ENTRYPOINT ["python"]
CMD ["/app/bootstrapper/bootstrapper.py"]
