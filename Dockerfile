FROM alpine:3.19 as builder

ENV HUGO_VER=0.124.1

RUN sed -i 's#dl-cdn.alpinelinux.org#mirrors.volces.com#g' /etc/apk/repositories && \
    apk add --no-cache curl tzdata && \
    curl -L "https://github.com/gohugoio/hugo/releases/download/v{$HUGO_VER}/hugo_${HUGO_VER}_linux-amd64.tar.gz" | tar zx -C /usr/local/bin/

COPY . /app/

WORKDIR /app/

RUN cd /app && \
    hugo --gc --minify


FROM nginx:1.25-alpine

COPY --from=builder /app/public /app

RUN cat <<EOF > /etc/nginx/nginx.conf
user                 nginx;
pid                  /var/run/nginx.pid;
worker_processes     auto;
worker_rlimit_nofile 65535;

events {
    multi_accept       on;
    worker_connections 65535;
}

http {
    charset                utf-8;
    sendfile               on;
    tcp_nopush             on;
    tcp_nodelay            on;
    server_tokens          off;
    log_not_found          off;
    types_hash_max_size    2048;
    types_hash_bucket_size 64;
    client_max_body_size   16M;

    # MIME
    include                mime.types;
    default_type           application/octet-stream;

    # Logging
    access_log             off;
    error_log              /dev/null;

    # gzip
    gzip            on;
    gzip_vary       on;
    gzip_proxied    any;
    gzip_comp_level 6;
    gzip_types      text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    server {
        listen      80;
        listen      [::]:80;
        server_name kdefan.net;
        root        /app;
        index       index.html;

        # security headers
        add_header X-XSS-Protection        "1; mode=block" always;
        add_header X-Content-Type-Options  "nosniff" always;
        add_header Referrer-Policy         "no-referrer-when-downgrade" always;
        add_header Content-Security-Policy "default-src 'self' http: https: ws: wss: data: blob: 'unsafe-inline'; frame-ancestors 'self';" always;
        add_header Permissions-Policy      "interest-cohort=()" always;

        # . files
        location ~ /\.(?!well-known) {
            deny all;
        }

        # logging
        access_log  /dev/stdout combined buffer=512k flush=1m;
        error_log   /dev/stderr warn;

        # favicon.ico
        location = /favicon.ico {
            log_not_found off;
        }

        # robots.txt
        location = /robots.txt {
            log_not_found off;
        }

        # assets, media
        location ~* \.(?:css(\.map)?|js(\.map)?|jpe?g|png|gif|ico|cur|heic|webp|tiff?|mp3|m4a|aac|ogg|midi?|wav|mp4|mov|webm|mpe?g|avi|ogv|flv|wmv)$ {
            expires 7d;
        }

        # svg, fonts
        location ~* \.(?:svgz?|ttf|ttc|otf|eot|woff2?)$ {
            add_header Access-Control-Allow-Origin "*";
            expires    7d;
        }
    }

    # subdomains redirect
    server {
        listen      80;
        listen      [::]:80;
        server_name *.kdefan.net;
        return      301 http://kdefan.net$request_uri;
    }
}
EOF
