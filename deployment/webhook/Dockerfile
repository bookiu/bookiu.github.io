FROM golang:1.20 AS builder

ENV GOPROXY="https://goproxy.cn,direct"
ENV GOPRIVATE=""

WORKDIR /usr/src/app

COPY go.mod go.sum ./
RUN go env -w GO111MODULE=on && \
    go env -w GOPROXY="https://goproxy.cn,direct" && \
    go env -w GOPRIVATE="" && \
    go mod download && go mod verify

COPY . .
RUN go build -v -o deploy-api


FROM yaxin/debian

WORKDIR /app

COPY --from=builder /usr/src/app/deploy-api /app/deploy-api

EXPOSE 8080

CMD ["/app/deploy-api"]
