package editor

import (
	"testing"
)

func TestDocument(t *testing.T) {
	path := "test.txt"
	initialContent := "Hello World"
	doc := NewDocument(path, initialContent)

	t.Run("Initial State", func(t *testing.T) {
		if doc.Path != path {
			t.Errorf("expected path %s, got %s", path, doc.Path)
		}
		if doc.GetContent() != initialContent {
			t.Errorf("expected content %s, got %s", initialContent, doc.GetContent())
		}
		if doc.IsDirty() {
			t.Error("expected new document to be clean")
		}
	})

	t.Run("Modify Content", func(t *testing.T) {
		newContent := "Hello YuMo Editor"
		doc.SetContent(newContent)
		if doc.GetContent() != newContent {
			t.Errorf("expected content %s, got %s", newContent, doc.GetContent())
		}
		if !doc.IsDirty() {
			t.Error("expected document to be dirty after modification")
		}
	})

	t.Run("Set Same Content", func(t *testing.T) {
		// Reset dirty for testing
		doc.MarkClean()
		content := doc.GetContent()
		doc.SetContent(content)
		if doc.IsDirty() {
			t.Error("expected document to remain clean when content is not changed")
		}
	})

	t.Run("Mark Clean", func(t *testing.T) {
		doc.SetContent("Change")
		doc.MarkClean()
		if doc.IsDirty() {
			t.Error("expected document to be clean after MarkClean()")
		}
	})
}
