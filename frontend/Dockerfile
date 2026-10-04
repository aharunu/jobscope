FROM node:20-bookworm-slim

ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY --chown=node:node src ./src
COPY --chown=node:node next.config.mjs tsconfig.json ./
RUN mkdir -p .next && chown node:node /app /app/.next

USER node
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
