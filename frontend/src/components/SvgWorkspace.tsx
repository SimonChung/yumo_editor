import { useEffect, useState } from 'react';
import { PreviewWorkspace, type WorkspaceProps } from './PreviewWorkspace';
import './SvgWorkspace.css';

function SvgPreview({ content }: { content: string }) {
    const [imageUrl, setImageUrl] = useState<string>();

    useEffect(() => {
        // An inert template preserves the SVG namespace for inline-style SVG files.
        const template = document.createElement('template');
        template.innerHTML = content;
        const svg = template.content.querySelector('svg');
        if (!svg) {
            setImageUrl(undefined);
            return;
        }

        const markup = new XMLSerializer().serializeToString(svg);
        const url = URL.createObjectURL(new Blob([markup], { type: 'image/svg+xml' }));
        setImageUrl(url);
        return () => URL.revokeObjectURL(url);
    }, [content]);

    return imageUrl ? <img key={imageUrl} src={imageUrl} className="svg-preview-image" alt="SVG 預覽" /> : null;
}

export function SvgWorkspace(props: WorkspaceProps) {
    return (
        <PreviewWorkspace {...props} format="SVG" language="markup">
            <SvgPreview content={props.content} />
        </PreviewWorkspace>
    );
}
