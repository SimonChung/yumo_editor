package main

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestContextMenuStartupArguments(t *testing.T) {
	previous := os.Args
	t.Cleanup(func() { os.Args = previous })
	a := NewApp()
	os.Args = []string{"YuMo Editor.exe"}
	if got := a.GetStartupFiles(); len(got) != 0 {
		t.Fatalf("empty startup: %v", got)
	}
	dir := t.TempDir()
	first := filepath.Join(dir, "中文 空白.txt")
	second := filepath.Join(dir, "other.md")
	for _, name := range []string{first, second} {
		if err := os.WriteFile(name, []byte("startup content"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	os.Args = []string{"YuMo Editor.exe", first, second}
	got := a.GetStartupFiles()
	if !reflect.DeepEqual(got, []string{first, second}) {
		t.Fatalf("startup paths changed: %v", got)
	}
	got[0] = "must not modify os.Args"
	if os.Args[1] != first {
		t.Fatal("returned paths alias process arguments")
	}
}
