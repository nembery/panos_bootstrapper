# Running Bootstrapper

The easiest way to run this tool is with docker

```bash
docker build -t panos_bootstrapper:v0.1 . 
docker run --entrypoint python -p 8002:5000 --name panos_bootstrapper panos_bootstrapper:v0.1 /app/bootstrapper/bootstrapper.py
```


