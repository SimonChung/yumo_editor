import { useMemo } from 'react';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { PreviewWorkspace, type WorkspaceProps } from './PreviewWorkspace';
import './MarkdownWorkspace.css';

export function MarkdownWorkspace(props: WorkspaceProps) {
    const { content } = props;
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
        <PreviewWorkspace {...props} format="Markdown" language="markdown">
            <article dangerouslySetInnerHTML={{ __html: previewHtml }} />
        </PreviewWorkspace>
    );
}
