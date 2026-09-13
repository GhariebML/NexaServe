FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache git python3 make g++

COPY package*.json ./
RUN npm install --omit=dev

COPY server.js ./

ENV PORT=8080
ENV AUTH_DIR=/app/data/auth
ENV N8N_WEBHOOK_URL=http://cs-n8n:5678/webhook/customer-service

EXPOSE 8080

CMD ["node", "server.js"]
