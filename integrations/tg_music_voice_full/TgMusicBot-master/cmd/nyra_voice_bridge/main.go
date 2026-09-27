package main

// NYRA Voice Bridge is an additive adapter around the supplied TgMusicBot.
// It does not replace or delete any original TgMusicBot source.  It exposes
// only the media-control operations NYRA needs over localhost HTTP.

import (
	"ashokshau/tgmusic/internal/calls"
	"ashokshau/tgmusic/internal/config"
	"ashokshau/tgmusic/internal/db"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/AshokShau/gotdbot"
)

type request struct {
	ChatID int64  `json:"chat_id"`
	Path   string `json:"path"`
	Video  bool   `json:"video"`
}

type response struct {
	OK    bool   `json:"ok"`
	Error string `json:"error,omitempty"`
}

var botClient *gotdbot.Client
var authToken = strings.TrimSpace(os.Getenv("NYRA_TG_VOICE_BRIDGE_TOKEN"))

func main() {
	if err := config.LoadEnv(); err != nil {
		panic(err)
	}
	if err := db.InitDatabase(); err != nil {
		panic("failed to connect database: " + err.Error())
	}

	libPath := os.Getenv("TG_BOT_LIBTDJSON")
	if libPath == "" {
		libPath = "./libtdjson.so.1.8.67"
	}
	manager := gotdbot.NewClientManager(libPath)
	cc := gotdbot.DefaultClientConfig()
	cc.DatabaseDirectory = "td_nyra_bridge"
	client, err := manager.RegisterClient(config.ApiId, config.ApiHash, config.Token, cc)
	if err != nil {
		panic("failed to register Telegram client: " + err.Error())
	}
	botClient = client

	for i, session := range config.SessionStrings {
		if err := calls.Calls.StartClient(config.ApiId, config.ApiHash, session, fmt.Sprintf("_nyra_%d", i)); err != nil {
			slog.Warn("assistant session failed", "index", i, "error", err)
		}
	}
	calls.Calls.RegisterHandlers(client)

	mux := http.NewServeMux()
	mux.HandleFunc("/health", health)
	mux.HandleFunc("/play", play)
	mux.HandleFunc("/pause", pause)
	mux.HandleFunc("/resume", resume)
	mux.HandleFunc("/stop", stop)
	mux.HandleFunc("/mute", mute)
	mux.HandleFunc("/unmute", unmute)

	addr := os.Getenv("NYRA_TG_VOICE_BRIDGE_ADDR")
	if addr == "" {
		addr = "127.0.0.1:8765"
	}
	srv := &http.Server{Addr: addr, Handler: auth(mux), ReadHeaderTimeout: 5 * time.Second}
	slog.Info("NYRA TgMusicBot voice bridge listening", "addr", addr)
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		panic(err)
	}
}

func auth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if authToken != "" && r.Header.Get("X-NYRA-Bridge-Token") != authToken {
			write(w, http.StatusUnauthorized, response{Error: "unauthorized"})
			return
		}
		next.ServeHTTP(w, r)
	})
}

func health(w http.ResponseWriter, r *http.Request) {
	write(w, http.StatusOK, response{OK: true})
}

func play(w http.ResponseWriter, r *http.Request) {
	var req request
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		write(w, http.StatusBadRequest, response{Error: err.Error()})
		return
	}
	if req.ChatID >= 0 || req.Path == "" {
		write(w, http.StatusBadRequest, response{Error: "chat_id must be a group id and path is required"})
		return
	}
	clean := filepath.Clean(req.Path)
	if clean != req.Path {
		write(w, http.StatusBadRequest, response{Error: "invalid path"})
		return
	}
	if _, err := os.Stat(clean); err != nil {
		write(w, http.StatusBadRequest, response{Error: "media file not found"})
		return
	}
	if err := calls.Calls.PlayMedia(botClient, req.ChatID, clean, req.Video); err != nil {
		write(w, http.StatusBadGateway, response{Error: err.Error()})
		return
	}
	write(w, http.StatusOK, response{OK: true})
}

func pause(w http.ResponseWriter, r *http.Request)  { callControl(w, r, "pause") }
func resume(w http.ResponseWriter, r *http.Request) { callControl(w, r, "resume") }
func stop(w http.ResponseWriter, r *http.Request)   { callControl(w, r, "stop") }
func mute(w http.ResponseWriter, r *http.Request)   { callControl(w, r, "mute") }
func unmute(w http.ResponseWriter, r *http.Request) { callControl(w, r, "unmute") }

func callControl(w http.ResponseWriter, r *http.Request, op string) {
	var req struct {
		ChatID int64 `json:"chat_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		write(w, http.StatusBadRequest, response{Error: err.Error()})
		return
	}
	var err error
	switch op {
	case "pause":
		_, err = calls.Calls.Pause(req.ChatID)
	case "resume":
		_, err = calls.Calls.Resume(req.ChatID)
	case "mute":
		_, err = calls.Calls.Mute(req.ChatID)
	case "unmute":
		_, err = calls.Calls.Unmute(req.ChatID)
	case "stop":
		err = calls.Calls.Stop(req.ChatID, false)
	default:
		err = errors.New("unsupported operation")
	}
	if err != nil {
		write(w, http.StatusBadGateway, response{Error: err.Error()})
		return
	}
	write(w, http.StatusOK, response{OK: true})
}

func write(w http.ResponseWriter, status int, v response) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

var _ = context.Background
