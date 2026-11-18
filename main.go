package main

import (
	"embed"
	"log"
	"net/http"
	"net/http/httputil"
	"os"

	"github.com/wailsapp/wails/v3/pkg/application"
	"github.com/wailsapp/wails/v3/pkg/events"
)

//go:embed frontend/dist/*
var assets embed.FS

func main() {
	// Create an instance of the app structure
	app := NewApp()
	workingDir, err := os.Getwd()
	if err != nil {
		log.Fatal(err)
	}
	app.queueLaunchFiles(os.Args, workingDir)

	assetHandler := application.AssetFileServerFS(assets)
	if proxy, ok := assetHandler.(*httputil.ReverseProxy); ok {
		// The Windows WebView uses wails.localhost. Forward the dev server's
		// own Host header when Wails proxies asset requests to esbuild.
		direct := proxy.Director
		proxy.Director = func(req *http.Request) {
			direct(req)
			req.Host = req.URL.Host
		}
	}

	// Create application with options
	wailsApp := application.New(application.Options{
		Name: "YuMo Editor",
		SingleInstance: &application.SingleInstanceOptions{
			UniqueID: "tw.ybak.yumo.editor",
			OnSecondInstanceLaunch: func(data application.SecondInstanceData) {
				app.queueLaunchFiles(data.Args, data.WorkingDir)
			},
		},
		Assets: application.AssetOptions{
			Handler: assetHandler,
		},
		Services: []application.Service{
			application.NewService(app),
		},
	})

	// Create the main window
	mainWindow := wailsApp.Window.NewWithOptions(application.WebviewWindowOptions{
		Title:            "玉墨",
		Width:            1024,
		Height:           768,
		BackgroundColour: application.NewRGBA(27, 38, 54, 255),
		EnableFileDrop:   true,
	})

	app.setLaunchFilesNotifier(func() {
		wailsApp.Event.Emit("launch-files-pending")
		mainWindow.UnMinimise()
		mainWindow.Show()
		mainWindow.Focus()
	})

	// Wails resolves Explorer drops to native absolute paths. Forward those paths
	// to React instead of trying to reconstruct them from browser File objects.
	mainWindow.OnWindowEvent(events.Common.WindowFilesDropped, func(event *application.WindowEvent) {
		files := event.Context().DroppedFiles()
		wailsApp.Event.Emit("files-dropped", map[string]any{"files": files})
	})

	// Run the application
	err = wailsApp.Run()
	if err != nil {
		log.Fatal(err)
	}
}
