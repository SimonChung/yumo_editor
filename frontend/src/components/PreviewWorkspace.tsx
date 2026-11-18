import { useState, type ReactNode } from 'react';
import { Editor } from './Editor';
import './PreviewWorkspace.css';

export interface WorkspaceProps {
    content: string;
    onChange: (value: string) => void;
    fontSize: number;
}

const modes = [
    ['edit', '編輯'],
    ['split', '分割預覽'],
    ['preview', '預覽'],
] as const;

interface PreviewWorkspaceProps extends WorkspaceProps {
    format: string;
    language: string;
    children: ReactNode;
}

export function PreviewWorkspace({ format, language, children, ...editor }: PreviewWorkspaceProps) {
    const [view, setView] = useState<typeof modes[number][0]>('split');

    return (
        <section className="preview-workspace" aria-label={`${format} editor and preview`}>
            <div className="preview-toolbar" role="toolbar" aria-label={`${format} view mode`}>
                {modes.map(([mode, label]) => (
                    <button type="button" key={mode} aria-pressed={view === mode} onClick={() => setView(mode)}>
                        {label}
                    </button>
                ))}
            </div>
            <div className={`preview-content preview-content-${view}`}>
                {view !== 'preview' && (
                    <div className="preview-editor-pane"><Editor {...editor} language={language} embedded /></div>
                )}
                {view === 'split' && <div className="preview-pane-divider" />}
                {view !== 'edit' && (
                    <div className={`preview-pane ${format.toLowerCase()}-preview-pane`} style={{ fontSize: editor.fontSize }}>
                        {children}
                    </div>
                )}
            </div>
        </section>
    );
}
