package fs

import (
	"bytes"
	"io"
	"os"
	"strings"
	"unicode/utf8"

	"golang.org/x/net/html/charset"
	"golang.org/x/text/encoding/simplifiedchinese"
	"golang.org/x/text/encoding/traditionalchinese"
	"golang.org/x/text/transform"
)

// decodeToUTF8 attempts to decode the data using the provided transformer, verifying that the result is valid UTF-8.
func decodeToUTF8(data []byte, enc transform.Transformer) ([]byte, error) {
	reader := transform.NewReader(bytes.NewReader(data), enc)
	decoded, err := io.ReadAll(reader)
	if err != nil {
		return nil, err
	}
	if !utf8.Valid(decoded) {
		return nil, io.ErrUnexpectedEOF
	}
	return decoded, nil
}

// ReadFile reads the content of the file at the given path and automatically detects and converts encoding to UTF-8 if necessary.
// It returns the decoded content, the detected original encoding name, and any error.
func ReadFile(path string) ([]byte, string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, "", err
	}

	// 1. If it is valid UTF-8 (which includes pure ASCII), return as is.
	if utf8.Valid(data) {
		return data, "UTF-8", nil
	}

	// 2. Prioritize Traditional Chinese (BIG5) and Simplified Chinese (GBK) probing.
	// Very short files often lack enough entropy for standard charset libraries to distinguish them from Windows-1252.
	if decoded, err := decodeToUTF8(data, traditionalchinese.Big5.NewDecoder()); err == nil {
		return decoded, "BIG5", nil
	}
	if decoded, err := decodeToUTF8(data, simplifiedchinese.GBK.NewDecoder()); err == nil {
		return decoded, "GBK", nil
	}

	// 3. Fallback to standard W3C HTML/Plain text auto-detect.
	enc, name, _ := charset.DetermineEncoding(data, "text/plain")
	if enc != nil && name != "utf-8" {
		if decoded, err := decodeToUTF8(data, enc.NewDecoder()); err == nil {
			return decoded, strings.ToUpper(name), nil
		}
	}

	// 4. Downgrade to original raw bytes if all else fails.
	return data, "UTF-8", nil
}

// IsBinary checks if the given data represents binary content rather than plain text.
func IsBinary(data []byte) bool {
	if len(data) == 0 {
		return false
	}

	// 1. Check for NUL byte (0x00), which is a definitive indicator of binary content.
	if bytes.IndexByte(data, 0) != -1 {
		return true
	}

	// 2. Check for control characters (0x01-0x08, 0x0B, 0x0C, 0x0E-0x1F) in the first 8000 bytes.
	// We allow common whitespace characters: Tab (0x09), LF (0x0A), CR (0x0D).
	// We also allow the DOS EOF marker (0x1A) in case it is an old text file.
	limit := 8000
	if len(data) < limit {
		limit = len(data)
	}

	for i := 0; i < limit; i++ {
		b := data[i]
		if (b < 32 && b != 9 && b != 10 && b != 13 && b != 26) || b == 127 {
			return true
		}
	}

	return false
}

// WriteFile writes the given content to the file at the given path.
func WriteFile(path string, content []byte) error {
	return os.WriteFile(path, content, 0644)
}

// WriteFileWithEncoding writes the string content to a file, encoding it into the target encoding (e.g. "BIG5", "GBK", "UTF-8").
func WriteFileWithEncoding(path string, content string, encodingName string) error {
	var data []byte
	var err error

	encodingName = strings.ToUpper(encodingName)
	switch encodingName {
	case "BIG5":
		encoder := traditionalchinese.Big5.NewEncoder()
		data, err = encoder.Bytes([]byte(content))
		if err != nil {
			return err
		}
	case "GBK":
		encoder := simplifiedchinese.GBK.NewEncoder()
		data, err = encoder.Bytes([]byte(content))
		if err != nil {
			return err
		}
	default:
		// Default to UTF-8
		data = []byte(content)
	}

	return os.WriteFile(path, data, 0644)
}
