// Wails v3 runtime type declarations
// This file provides TypeScript type hints for the Wails v3 runtime
// that is injected into the window object at runtime.

interface WailsCall {
    ByName(methodName: string, ...args: any[]): Promise<any>;
    ByID(id: number, ...args: any[]): Promise<any>;
}

interface WailsRuntime {
    Call: WailsCall;
}

declare global {
    interface Window {
        wails: WailsRuntime;
    }
}

export {};
