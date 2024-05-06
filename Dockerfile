FROM nginx:1.25-alpine

COPY --chown=nginx:nginx ./public/ /data/release/kdefan.net/

COPY nginx.conf /etc/nginx/nginx.conf

RUN ln -s /data/release/kdefan.net /app

WORKDIR /data/release/kdefan.net

EXPOSE 80
