FROM node:22-alpine AS builder

WORKDIR /app

#better Docker cache
COPY package.json package-lock.json ./

RUN npm ci


COPY . .

# Default is relative /api (Ingress / Nginx reverse proxy).
# Override only if you must point at a full URL.
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Final image
FROM nginx:1.27-alpine


COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from stage 1.
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
