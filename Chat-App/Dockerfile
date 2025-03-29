FROM node:18

# Set working directory in the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json to install dependencies
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application files to the container
COPY . .

# Set environment variables for PostgreSQL connection
ENV PGUSER=postgres
ENV PGHOST=10.239.0.3
ENV PGDATABASE=chatdb
ENV PGPASSWORD=postgres
ENV PGPORT=5432

# Expose port 5000 for the app
EXPOSE 5000

# Start the app
CMD ["node", "app.js"]
