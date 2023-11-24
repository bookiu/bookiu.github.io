FROM alpine

RUN apk add --no-cache rsync nginx

COPY nginx.conf /etc/nginx/

CMD [ "nginx", "-g", "daemon off;" ]
