module tw.ybak/yumo

go 1.27.4

require (
	github.com/wailsapp/wails/v3 v3.1.0
	golang.org/x/net v0.62.0 // direct
	golang.org/x/text v0.43.0 // direct
)

require (
	github.com/coder/websocket v1.8.14 // indirect
	github.com/ebitengine/purego v0.11.1 // indirect
	github.com/go-ole/go-ole v1.3.0 // indirect
	github.com/godbus/dbus/v5 v5.2.2 // indirect
	golang.org/x/sys v0.49.0 // indirect
	golang.org/x/term v0.47.0 // indirect
)

// Constrain vulnerable transitive selections, including unused modules in the full graph.
replace github.com/klauspost/compress v1.18.3 => github.com/klauspost/compress v1.20.2

replace github.com/yuin/goldmark v1.7.16 => github.com/yuin/goldmark v1.7.17

replace golang.org/x/crypto v0.58.0 => golang.org/x/crypto v0.58.1-0.20261009181718-2f1f834330b2

replace golang.org/x/image v0.41.0 => golang.org/x/image v0.45.0
