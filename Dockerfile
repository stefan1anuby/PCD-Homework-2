FROM node:18

# Create app directory
WORKDIR /usr/src/app

# Copy package.json and install dependencies
COPY package*.json ./
RUN npm install

COPY . .

# Copy source files

EXPOSE 5000
CMD ["node", "app.js"]
