FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy all files
COPY . .

# Run Next.js in development mode
CMD ["npm", "run", "dev"]
