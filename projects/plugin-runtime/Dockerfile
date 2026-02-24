FROM node:20-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install --production

COPY ./src ./src
COPY tsconfig.json ./

RUN npm run build

EXPOSE 3001

CMD ["node", "dist/index.js"]
