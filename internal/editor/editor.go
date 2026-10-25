package editor

import (
	"sync"
)

// Document represents an open file in the editor.
type Document struct {
	mu       sync.RWMutex
	Path     string
	Content  string
	isDirty  bool
}

// NewDocument creates a new Document instance.
func NewDocument(path, content string) *Document {
	return &Document{
		Path:    path,
		Content: content,
		isDirty: false,
	}
}

// SetContent updates the document content and marks it as dirty.
func (d *Document) SetContent(content string) {
	d.mu.Lock()
	defer d.mu.Unlock()
	if d.Content != content {
		d.Content = content
		d.isDirty = true
	}
}

// GetContent returns the current content of the document.
func (d *Document) GetContent() string {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.Content
}

// IsDirty returns whether the document has unsaved changes.
func (d *Document) IsDirty() bool {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.isDirty
}

// MarkClean marks the document as having no unsaved changes.
func (d *Document) MarkClean() {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.isDirty = false
}
