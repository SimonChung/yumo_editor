#!/bin/bash

# macOS Build Script (converted from Makefile.mac)
BINARY_NAME="yumo_editor"

# Detect task executable
if command -v task >/dev/null 2>&1; then
    TASK_CMD="task"
elif [ -f "$HOME/go/bin/task" ]; then
    TASK_CMD="$HOME/go/bin/task"
else
    echo "[WARNING] 'task' command not found on PATH or in \$HOME/go/bin."
    echo "Please install it via: go install github.com/go-task/task/v3/cmd/task@latest"
    TASK_CMD="task"
fi

# Detect wails3 executable
if command -v wails3 >/dev/null 2>&1; then
    WAILS_CMD="wails3"
elif [ -f "$HOME/go/bin/wails3" ]; then
    WAILS_CMD="$HOME/go/bin/wails3"
else
    echo "[WARNING] 'wails3' command not found on PATH or in \$HOME/go/bin."
    WAILS_CMD="wails3"
fi

# Handle arguments
TARGET="${1:-build}"

case "$TARGET" in
    all|build)
        echo "[build] Running: $TASK_CMD build"
        $TASK_CMD build
        ;;
    build_installer|build-installer)
        echo "[build_installer] Running: $TASK_CMD package"
        $TASK_CMD package
        ;;
    dev)
        echo "[dev] Running: $WAILS_CMD dev"
        $WAILS_CMD dev
        ;;
    clean)
        echo "[clean] Running: $TASK_CMD clean"
        $TASK_CMD clean
        ;;
    clean_all|clean-all)
        echo "[clean_all] Running: $TASK_CMD clean:all"
        $TASK_CMD clean:all
        ;;
    *)
        echo "Unknown target: $TARGET"
        echo "Usage: $0 [build | build_installer | dev | clean | clean_all]"
        exit 1
        ;;
esac

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "Execution completed successfully."
    exit 0
else
    echo "[ERROR] Execution failed!"
    exit $EXIT_CODE
fi
