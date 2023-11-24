package main

import (
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/api/types/container"
	"github.com/docker/docker/api/types/mount"
	"github.com/docker/docker/client"
	_ "go.uber.org/automaxprocs"
)

type DeployRequest struct {
	Image string `json:"Image"`
}

type DeployResponse struct {
	ContainerID string `json:"ContainerID"`
}

type ErrorResponse struct {
	Message string `json:"Message"`
}

var (
	DeployToken       = os.Getenv("DEPLOY_TOKEN")
	DefaultDeployPath = "/data/release/kdefan.net"

	lock sync.Mutex
)

func main() {
	http.HandleFunc("/deploy", func(w http.ResponseWriter, r *http.Request) {
		if !lock.TryLock() {
			// 永远只能有一个部署任务在运行
			w.WriteHeader(http.StatusForbidden)
			w.Write(packErrorResponse("Another deploy task is running"))
			return
		}
		defer lock.Unlock()

		// 从请求 Header 头获取 auth token，并校验 token 是否正确
		if !validateToken(r) {
			w.WriteHeader(http.StatusUnauthorized)
			w.Write(packErrorResponse("Unauthorized"))
			return
		}

		ctx := r.Context()

		// 校验方法
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			w.Write([]byte("Method Not Allowed"))
			return
		}

		// 获取需要部署的镜像
		req := &DeployRequest{}
		if err := json.NewDecoder(r.Body).Decode(req); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			w.Write(packErrorResponse(err.Error()))
			return
		}
		image := req.Image

		// 运行镜像进行部署
		containerID, err := runImage(ctx, image, getDeployPathFromEnv())
		if err != nil {
			w.WriteHeader(http.StatusInternalServerError)
			w.Write(packErrorResponse(err.Error()))
		}

		w.Write(packErrorResponse(containerID))
	})

	// ping路由
	http.HandleFunc("/ping", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("pong"))
	})

	log.Panic(http.ListenAndServe(":8080", nil))
}

// validateToken 检验部署 token
func validateToken(req *http.Request) bool {
	var token string
	authorization := req.Header.Get("Authorization")
	if strings.HasPrefix(authorization, "Bearer ") {
		token = authorization[7:]
	} else {
		token = authorization
	}
	if token == "" {
		return false
	}
	if token == DeployToken {
		return true
	}
	return false
}

// runImage 运行镜像
func runImage(ctx context.Context, image string, deployPath string) (string, error) {
	cli, err := client.NewClientWithOpts(client.FromEnv)
	if err != nil {
		return "", err
	}
	out, err := cli.ImagePull(ctx, image, types.ImagePullOptions{})
	if err != nil {
		return "", err
	}
	defer out.Close()
	io.Copy(os.Stdout, out)

	resp, err := cli.ContainerCreate(ctx, &container.Config{
		Image: image,
	}, &container.HostConfig{
		Mounts: []mount.Mount{
			{
				Type:   mount.TypeBind,
				Source: deployPath,
				Target: "/dest",
			},
		},
	}, nil, nil, "")
	if err != nil {
		return "", err
	}
	if err := cli.ContainerStart(ctx, resp.ID, types.ContainerStartOptions{}); err != nil {
		return "", err
	}
	return resp.ID, nil
}

// getDeployPathFromEnv 获取部署路径
func getDeployPathFromEnv() string {
	if v, ok := os.LookupEnv("DEPLOY_PATH"); ok {
		return v
	}
	return DefaultDeployPath
}

// getErrorResponse 获取错误响应
func packErrorResponse(err string) []byte {
	resp := &ErrorResponse{
		Message: err,
	}
	b, _ := json.Marshal(resp)
	return b
}

func packResposne(containerID string) []byte {
	resp := &DeployResponse{
		ContainerID: containerID,
	}
	b, _ := json.Marshal(resp)
	return b
}
