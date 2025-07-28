FROM --platform=linux/amd64 python:3.11.9

WORKDIR /app

# Copy the processing script
COPY . /app

# Run the script
RUN pip install -r requirments.txt
CMD ["python", "final.py"] 