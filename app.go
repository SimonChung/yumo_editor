package main

import (
	"context"
	"fmt"
	"path/filepath"
	"strings"

	"tw.ybak/yumo/internal/fs"

	"github.com/wailsapp/wails/v3/pkg/application"
)

// App struct
type App struct {
	app *application.App
}

// NewApp creates a new App application struct
func NewApp() *App {
	return &App{}
}

// ServiceStartup is called when the service starts.
// It replaces the v2 startup(ctx) lifecycle hook.
func (a *App) ServiceStartup(ctx context.Context, options application.ServiceOptions) error {
	a.app = application.Get()
	return nil
}

// FileResult 包含檔案內容與偵測到的編碼名稱
type FileResult struct {
	Content  string `json:"content"`
	Encoding string `json:"encoding"`
}

// OpenFile 讀取指定路徑的檔案內容與編碼
func (a *App) OpenFile(path string) (*FileResult, error) {
	bytes, enc, err := fs.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("讀取檔案失敗: %w", err)
	}

	// 判斷是否為非文字檔 (二進位檔)
	if fs.IsBinary(bytes) {
		if a.app != nil {
			dialog := a.app.Dialog.Info().
				SetTitle("無法讀取檔案").
				SetMessage(fmt.Sprintf("檔案「%s」為非文字檔，無法讀取。", filepath.Base(path)))
			if win := a.app.Window.Current(); win != nil {
				dialog.AttachToWindow(win)
			}
			dialog.Show()
		}
		return nil, nil
	}

	return &FileResult{
		Content:  string(bytes),
		Encoding: enc,
	}, nil
}

// SaveFile 將內容與指定的編碼格式寫入指定路徑的檔案中
func (a *App) SaveFile(path string, content string, encoding string) error {
	err := fs.WriteFileWithEncoding(path, content, encoding)
	if err != nil {
		return fmt.Errorf("儲存檔案失敗: %w", err)
	}
	return nil
}

// SelectFile 喚起系統原生開啟檔案對話框，返回選擇的檔案路徑
func (a *App) SelectFile() (string, error) {
	path, err := a.app.Dialog.OpenFileWithOptions(&application.OpenFileDialogOptions{
		Title: "選擇要開啟的檔案",
		Filters: []application.FileFilter{
			{DisplayName: "文字與程式碼檔案 (*.txt;*.md;*.go;*.js;*.ts;*.json;*.css;*.html)", Pattern: "*.txt;*.md;*.go;*.js;*.ts;*.json;*.css;*.html"},
			{DisplayName: "所有檔案 (*.*)", Pattern: "*.*"},
		},
	}).PromptForSingleSelection()
	if err != nil {
		if strings.Contains(strings.ToLower(err.Error()), "cancel") {
			return "", nil
		}
		return "", fmt.Errorf("開啟檔案對話框失敗: %w", err)
	}
	return path, nil
}

// SelectSaveFile 喚起系統原生儲存檔案對話框，返回選擇的儲存路徑
func (a *App) SelectSaveFile(defaultName string) (string, error) {
	path, err := a.app.Dialog.SaveFileWithOptions(&application.SaveFileDialogOptions{
		Title:    "選擇儲存位置",
		Filename: defaultName,
		Filters: []application.FileFilter{
			{DisplayName: "文字檔案 (*.txt)", Pattern: "*.txt"},
			{DisplayName: "Markdown 檔案 (*.md)", Pattern: "*.md"},
			{DisplayName: "所有檔案 (*.*)", Pattern: "*.*"},
		},
	}).PromptForSingleSelection()
	if err != nil {
		if strings.Contains(strings.ToLower(err.Error()), "cancel") {
			return "", nil
		}
		return "", fmt.Errorf("儲存檔案對話框失敗: %w", err)
	}
	return path, nil
}
