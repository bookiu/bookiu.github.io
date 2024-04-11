FROM yaxin/blog-site-base

COPY ./public/ /app/

CMD [ "rsync", "--progress", "--delete", "-avzh", "/app/", "/dest/" ]
