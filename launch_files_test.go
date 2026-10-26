package main

import (
	"fmt"
	"path/filepath"
	"reflect"
	"sync"
	"testing"
)

func TestLaunchFilesSurviveStartupAndUseSenderWorkingDirectory(t *testing.T) {
	a := NewApp()
	firstDir, secondDir := t.TempDir(), t.TempDir()
	firstPath := filepath.Join(firstDir, "中文 筆記.txt")
	secondPath := filepath.Join(secondDir, "說明.md")
	// Neither the window nor its frontend listener exists yet.
	a.queueLaunchFiles([]string{"yumo_editor.exe", firstPath}, firstDir)
	a.queueLaunchFiles([]string{"yumo_editor.exe", "說明.md", ""}, secondDir)
	if got := a.TakeLaunchFiles(); !reflect.DeepEqual(got, []string{firstPath, secondPath}) {
		t.Fatalf("pending files = %q", got)
	}
	if got := a.TakeLaunchFiles(); got == nil || len(got) != 0 {
		t.Fatalf("drained queue must serialize as an empty array, got %#v", got)
	}
}

func TestLaunchNotificationCanDrainWithoutDeadlock(t *testing.T) {
	a := NewApp()
	var got []string
	notifications := 0
	a.setLaunchFilesNotifier(func() {
		notifications++
		got = append(got, a.TakeLaunchFiles()...)
	})
	dir := t.TempDir()
	// Preserve missing paths so the normal open-file UI can explain the error.
	a.queueLaunchFiles([]string{"yumo_editor.exe", "missing.txt"}, dir)
	a.queueLaunchFiles([]string{"yumo_editor.exe"}, dir)
	a.queueLaunchFiles(nil, dir)
	if notifications != 3 || !reflect.DeepEqual(got, []string{filepath.Join(dir, "missing.txt")}) {
		t.Fatalf("notifications = %d, files = %q", notifications, got)
	}
}

func TestConcurrentLaunchesAreNotLostOrReplayed(t *testing.T) {
	a := NewApp()
	dir := t.TempDir()
	var wg sync.WaitGroup
	const count = 50
	for i := 0; i < count; i++ {
		wg.Go(func() {
			a.queueLaunchFiles([]string{"yumo_editor.exe", fmt.Sprintf("file-%d.txt", i)}, dir)
		})
	}
	// Drain while requests are arriving, as the frontend does on notifications.
	var got []string
	for i := 0; i < count; i++ {
		got = append(got, a.TakeLaunchFiles()...)
	}
	wg.Wait()
	got = append(got, a.TakeLaunchFiles()...)
	seen := make(map[string]bool)
	for _, path := range got {
		if seen[path] {
			t.Fatalf("replayed file %q", path)
		}
		seen[path] = true
	}
	if len(seen) != count {
		t.Fatalf("received %d of %d files", len(seen), count)
	}
}
