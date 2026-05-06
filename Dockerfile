# Use a base image with both Python 3.12 and Node.js 20
FROM nikolaik/python-nodejs:python3.12-nodejs20-slim

# Install required system packages
RUN apt-get update && apt-get install -y \
    git \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy your forked repository into the container
COPY . /app/

# Install UV (Python package manager required by OMC)
RUN pip install uv

# Ensure the container treats /root as the home directory 
# (This is where OMC stores its persistent .onemancompany data)
ENV HOME=/root

# Make the start script executable
RUN chmod +x start.sh

# Expose the default OMC port
EXPOSE 8000

# Start the application using their native script
CMD ["bash", "start.sh"]
