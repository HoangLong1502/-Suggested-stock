FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN rm -rf .next
EXPOSE 3000
CMD ["npm", "run", "dev"]
