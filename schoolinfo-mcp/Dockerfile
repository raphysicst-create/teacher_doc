FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY src ./src
COPY tsconfig.json tsup.config.ts ./
RUN npm run build

FROM node:22-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY --from=build /app/dist ./dist
COPY LICENSE NOTICE README.md ./
ENV PORT=8080
EXPOSE 8080
USER node
CMD ["node", "dist/server.js"]
