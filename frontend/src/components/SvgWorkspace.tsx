import { PreviewWorkspace, type WorkspaceProps } from './PreviewWorkspace';
import './SvgWorkspace.css';

export function SvgWorkspace(props: WorkspaceProps) {
    return (
        <PreviewWorkspace {...props} format="SVG" language="markup">
            <iframe title="SVG preview" className="svg-preview-frame" sandbox="" srcDoc={props.content} />
        </PreviewWorkspace>
    );
}
