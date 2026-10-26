package main

import "path/filepath"

// queueLaunchFiles accepts argv including the executable, as supplied by Wails.
// Keep requests until React subscribes and drains them; startup events alone can
// be lost while the WebView is still loading.
func (a *App) queueLaunchFiles(args []string, workingDir string) {
	var paths []string
	if len(args) > 1 {
		for _, path := range args[1:] {
			if path == "" {
				continue
			}
			if !filepath.IsAbs(path) {
				path = filepath.Join(workingDir, path)
			}
			absolute, err := filepath.Abs(path)
			if err == nil {
				paths = append(paths, absolute)
			}
		}
	}

	a.launchMu.Lock()
	a.pendingLaunchFiles = append(a.pendingLaunchFiles, paths...)
	notify := a.notifyLaunchFiles
	a.launchMu.Unlock()
	if notify != nil {
		notify()
	}
}

func (a *App) setLaunchFilesNotifier(notify func()) {
	a.launchMu.Lock()
	a.notifyLaunchFiles = notify
	a.launchMu.Unlock()
}

// TakeLaunchFiles returns pending command-line files exactly once. The frontend
// calls this after subscribing to notifications and after every later launch.
func (a *App) TakeLaunchFiles() []string {
	a.launchMu.Lock()
	defer a.launchMu.Unlock()
	paths := a.pendingLaunchFiles
	a.pendingLaunchFiles = nil
	if paths == nil {
		return []string{}
	}
	return paths
}
