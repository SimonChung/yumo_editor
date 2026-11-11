module tw.ybak/yumo

go 1.27.4

require (
	github.com/wailsapp/wails/v3 v3.0.0-beta.30
	golang.org/x/net v0.62.0 // direct
	golang.org/x/text v0.43.0 // direct
)

require (
	github.com/adrg/xdg v0.5.3 // indirect
	github.com/coder/websocket v1.8.14 // indirect
	github.com/go-ole/go-ole v1.3.0 // indirect
	github.com/godbus/dbus/v5 v5.2.2 // indirect
	github.com/mattn/go-colorable v0.1.14 // indirect
	github.com/mattn/go-isatty v0.0.20 // indirect
	golang.org/x/sys v0.49.0 // indirect
)

// Constrain vulnerable transitive selections, including unused modules in the full graph.
replace github.com/klauspost/compress v1.18.3 => github.com/klauspost/compress v1.20.2

replace github.com/yuin/goldmark v1.7.16 => github.com/yuin/goldmark v1.7.17

replace golang.org/x/crypto v0.58.0 => golang.org/x/crypto v0.58.1-0.20261009181718-2f1f834330b2

replace golang.org/x/image v0.41.0 => golang.org/x/image v0.45.0
