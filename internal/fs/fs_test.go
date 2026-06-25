package fs

import (
	"os"
	"path/filepath"
	"testing"
)

func TestReadFile(t *testing.T) {
	content := []byte("Hello, YuMo Editor!")
	tmpFile := filepath.Join(t.TempDir(), "test.txt")

	if err := os.WriteFile(tmpFile, content, 0644); err != nil {
		t.Fatalf("failed to setup test file: %v", err)
	}

	t.Run("Successful Read", func(t *testing.T) {
		got, enc, err := ReadFile(tmpFile)
		if err != nil {
			t.Errorf("ReadFile() error = %v, wantErr %v", err, false)
		}
		if enc != "UTF-8" {
			t.Errorf("ReadFile() encoding = %v, want %v", enc, "UTF-8")
		}
		if string(got) != string(content) {
			t.Errorf("ReadFile() = %v, want %v", string(got), string(content))
		}
	})

	t.Run("File Not Found", func(t *testing.T) {
		_, _, err := ReadFile("non_existent_file.txt")
		if err == nil {
			t.Error("ReadFile() expected error for non-existent file, got nil")
		}
	})
}

func TestWriteFile(t *testing.T) {
	content := []byte("New content for YuMo Editor")
	tmpFile := filepath.Join(t.TempDir(), "write_test.txt")

	t.Run("Successful Write", func(t *testing.T) {
		err := WriteFile(tmpFile, content)
		if err != nil {
			t.Errorf("WriteFile() error = %v, wantErr %v", err, false)
		}

		got, err := os.ReadFile(tmpFile)
		if err != nil {
			t.Fatalf("failed to read back written file: %v", err)
		}
		if string(got) != string(content) {
			t.Errorf("WriteFile() content = %v, want %v", string(got), string(content))
		}
	})

	t.Run("Write to Invalid Path", func(t *testing.T) {
		err := WriteFile("/invalid/path/to/file.txt", content)
		if err == nil {
			t.Error("WriteFile() expected error for invalid path, got nil")
		}
	})
}

func TestReadFileAutoDetect(t *testing.T) {
	// 1. 測試 ASCII (也是合法的 UTF-8)
	asciiContent := []byte("Hello ASCII")
	tmpASCII := filepath.Join(t.TempDir(), "ascii.txt")
	if err := os.WriteFile(tmpASCII, asciiContent, 0644); err != nil {
		t.Fatalf("setup failed: %v", err)
	}
	got, enc, err := ReadFile(tmpASCII)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if enc != "UTF-8" {
		t.Errorf("got encoding %q, want %q", enc, "UTF-8")
	}
	if string(got) != "Hello ASCII" {
		t.Errorf("got %q, want %q", string(got), "Hello ASCII")
	}

	// 2. 測試 BIG5 檔案 (傳統繁體中文編碼)
	// "中文測試" 的 BIG5 位元組
	big5Bytes := []byte{0xa4, 0xa4, 0xa4, 0xe5, 0xb4, 0xfa, 0xb8, 0xd5}
	tmpBig5 := filepath.Join(t.TempDir(), "big5.txt")
	if err := os.WriteFile(tmpBig5, big5Bytes, 0644); err != nil {
		t.Fatalf("setup failed: %v", err)
	}

	gotBig5, encBig5, err := ReadFile(tmpBig5)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if encBig5 != "BIG5" {
		t.Errorf("got encoding %q, want %q", encBig5, "BIG5")
	}
	// 解碼後應該變成 UTF-8 的 "中文測試"
	if string(gotBig5) != "中文測試" {
		t.Errorf("got %q, want %q", string(gotBig5), "中文測試")
	}
}

func TestIsBinary(t *testing.T) {
	tests := []struct {
		name     string
		content  []byte
		isBinary bool
	}{
		{"Empty content", []byte(""), false},
		{"ASCII text", []byte("Hello, world! 123 \t\r\n"), false},
		{"Chinese UTF-8", []byte("哈囉，世界！"), false},
		{"Chinese Big5-like bytes", []byte{0xa4, 0xa4, 0xa4, 0xe5, 0xb4, 0xfa, 0xb8, 0xd5}, false},
		{"Contains NUL byte", []byte("Hello\x00World"), true},
		{"Contains control char SOH", []byte("Hello\x01World"), true},
		{"Contains control char ETX", []byte("Hello\x03World"), true},
		{"Binary header PNG", []byte("\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"), true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := IsBinary(tt.content)
			if got != tt.isBinary {
				t.Errorf("IsBinary() = %v, want %v for %q", got, tt.isBinary, tt.name)
			}
		})
	}
}
