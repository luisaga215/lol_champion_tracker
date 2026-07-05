FROM node:20-slim

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000
ENV DATA_DIR=/app/data

# Create directory structure
WORKDIR /app
RUN mkdir -p /app/data

# Copy dependency definition
COPY package.json ./

# Install only production dependencies (Express & sqlite3)
RUN npm install --omit=dev

# Copy application source code
COPY src/ ./src

# Expose port
EXPOSE 3000

# Mountable volume for database and images persistence
VOLUME ["/app/data"]

# Run the server
CMD ["node", "src/server.js"]
