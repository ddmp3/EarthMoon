# Contexte de build = RACINE du dépôt :
#   docker build -f apps/api/Dockerfile -t analogues-api .
# (l'image embarque data/ : candidats, fixtures, profil lunaire)
FROM node:22-slim AS build
WORKDIR /repo/apps/api
COPY apps/api/package.json apps/api/package-lock.json ./
RUN npm ci
COPY apps/api/tsconfig.json apps/api/tsconfig.build.json ./
COPY apps/api/src ./src
RUN npm run build

FROM node:22-slim
ENV NODE_ENV=production \
    PORT=3001
WORKDIR /repo/apps/api
COPY apps/api/package.json apps/api/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /repo/apps/api/dist ./dist
COPY apps/api/openapi.yaml ./openapi.yaml
COPY data /repo/data
USER node
EXPOSE 3001
CMD ["node", "dist/server/index.js"]
