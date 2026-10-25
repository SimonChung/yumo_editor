import React, { useMemo, useState } from 'react';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { Editor } from './Editor';
import './MarkdownWorkspace.css';

type MarkdownView = 'edit' | 'split' | 'preview';

interface MarkdownWorkspaceProps {
    content: string;
    onChange: (value: string) => void;
    fontSize: number;
}

const viewLabels: Record<MarkdownView, string> = {
    edit: '編輯',
    split: '分割預覽',
    preview: '預覽',
};

export const MarkdownWorkspace: React.FC<MarkdownWorkspaceProps> = ({ content, onChange, fontSize }) => {
    const [view, setView] = useState<MarkdownView>('split');

    const previewHtml = useMemo(() => {
        const rendered = marked.parse(content, {
            async: false,
            breaks: true,
            gfm: true,
        });

        return DOMPurify.sanitize(rendered, {
            USE_PROFILES: { html: true },
        });
    }, [content]);

    return (
        <section className="markdown-workspace" aria-label="Markdown editor and preview">
            <div className="markdown-toolbar" role="toolbar" aria-label="Markdown view mode">
                {(Object.keys(viewLabels) as MarkdownView[]).map((mode) => (
                    <button
                        key={mode}
                        type="button"
                        className={`markdown-view-button ${view === mode ? 'active' : ''}`}
                        onClick={() => setView(mode)}
                        aria-pressed={view === mode}
                    >
                        {viewLabels[mode]}
                    </button>
                ))}
            </div>

            <div className={`markdown-content markdown-content-${view}`}>
                {view !== 'preview' && (
                    <div className="markdown-editor-pane">
                        <Editor
                            content={content}
                            onChange={onChange}
                            fontSize={fontSize}
                            language="markdown"
                            embedded
                        />
                    </div>
                )}

                {view === 'split' && <div className="markdown-pane-divider" />}

                {view !== 'edit' && (
                    <article
                        className="markdown-preview-pane"
                        style={{ fontSize: `${fontSize}px` }}
                        dangerouslySetInnerHTML={{ __html: previewHtml }}
                    />
                )}
            </div>
        </section>
    );
};
