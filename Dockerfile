FROM python:3.10-slim

WORKDIR /app
COPY . /app

# install dependencies
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# expose and run
EXPOSE 5000
CMD ["python", "main.py"]

