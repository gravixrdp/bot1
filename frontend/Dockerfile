FROM node:20-alpine

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

# Serve static with a tiny server
RUN npm i -g serve

EXPOSE 5173
CMD ["serve", "-s", "dist", "-l", "5173"]