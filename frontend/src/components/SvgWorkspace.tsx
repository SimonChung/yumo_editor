import React, { useState } from 'react';
import { Editor } from './Editor';
import './SvgWorkspace.css';

type SvgView = 'edit' | 'split' | 'preview';

interface SvgWorkspaceProps {
    content: string;
    onChange: (value: string) => void;
    fontSize: number;
}

const viewLabels: Record<SvgView, string> = {
    edit: '編輯',
    split: '分割預覽',
    preview: '預覽',
};

export const SvgWorkspace: React.FC<SvgWorkspaceProps> = ({ content, onChange, fontSize }) => {
    const [view, setView] = useState<SvgView>('split');

    return (
        <section className="svg-workspace" aria-label="SVG editor and preview">
            <div className="svg-toolbar" role="toolbar" aria-label="SVG view mode">
                {(Object.keys(viewLabels) as SvgView[]).map((mode) => (
                    <button key={mode} type="button" className={`svg-view-button ${view === mode ? 'active' : ''}`} onClick={() => setView(mode)} aria-pressed={view === mode}>
                        {viewLabels[mode]}
                    </button>
                ))}
            </div>
            <div className={`svg-content svg-content-${view}`}>
                {view !== 'preview' && <div className="svg-editor-pane"><Editor content={content} onChange={onChange} fontSize={fontSize} language="markup" embedded /></div>}
                {view === 'split' && <div className="svg-pane-divider" />}
                {view !== 'edit' && <div className="svg-preview-pane"><iframe title="SVG preview" className="svg-preview-frame" sandbox="" srcDoc={content} /></div>}
            </div>
        </section>
    );
};