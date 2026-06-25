import React, { useRef, useEffect } from 'react';
import Prism from 'prismjs';

// Setup Prism global for its plugins/languages to read
(window as any).Prism = Prism;

// Import languages
import 'prismjs/components/prism-clike';
import 'prismjs/components/prism-go';
import 'prismjs/components/prism-markup-templating';
import 'prismjs/components/prism-php';
import 'prismjs/components/prism-python';

// Import Tomorrow Theme CSS (dark mode compatible syntax coloring)
import 'prismjs/themes/prism-tomorrow.css';
import './Editor.css';

interface EditorProps {
    content: string;
    onChange: (value: string) => void;
    fontSize: number;
    language: string;
}

export const Editor: React.FC<EditorProps> = ({ content, onChange, fontSize, language }) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const gutterRef = useRef<HTMLDivElement>(null);
    const overlayRef = useRef<HTMLPreElement>(null);

    const lines = content.split('\n');

    // Synchronize scrolling between textarea, gutter, and highlight overlay
    const handleScroll = () => {
        if (textareaRef.current) {
            const { scrollTop, scrollLeft } = textareaRef.current;
            if (gutterRef.current) {
                gutterRef.current.scrollTop = scrollTop;
            }
            if (overlayRef.current) {
                overlayRef.current.scrollTop = scrollTop;
                overlayRef.current.scrollLeft = scrollLeft;
            }
        }
    };

    // When font size changes, re-sync the scroll position
    useEffect(() => {
        handleScroll();
    }, [fontSize]);

    // Format content with HTML escape and highlight using Prism
    const getHighlightedContent = (code: string, lang: string): string => {
        // Simple HTML Escape function to prevent HTML/XSS injection
        const escapeHtml = (text: string) => {
            return text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
        };

        if (!code) return ' ';

        // If plaintext or unsupported language, fallback to simple escaped text
        if (lang === 'plaintext' || !Prism.languages[lang]) {
            return escapeHtml(code);
        }

        try {
            let codeToHighlight = code;
            let isFakePhp = false;

            // PHP Special Handling: Prism requires "<?php" tag to kickstart PHP mode.
            // If the code doesn't start with it, temporarily prepend it.
            if (lang === 'php' && !code.trim().startsWith('<?php')) {
                codeToHighlight = '<?php\n' + code;
                isFakePhp = true;
            }

            let highlighted = Prism.highlight(codeToHighlight, Prism.languages[lang], lang);

            // Clean up the temporary PHP tag if prepended
            if (isFakePhp) {
                const linesArr = highlighted.split('\n');
                linesArr.shift(); // Remove the prepended '<?php\n' equivalent
                highlighted = linesArr.join('\n');
            }

            // Ensure trailing newline is rendered correctly (so that cursor height stays aligned in empty lines)
            if (code.endsWith('\n')) {
                highlighted += '\n ';
            }

            return highlighted;
        } catch (e) {
            console.error('Highlighting error:', e);
            return escapeHtml(code);
        }
    };

    const highlighted = getHighlightedContent(content, language);

    return (
        <div className="editor-container">
            {/* 行號區域 */}
            <div 
                className="editor-gutter" 
                ref={gutterRef}
                style={{ fontSize: `${fontSize}px` }}
            >
                {lines.map((_, index) => (
                    <div key={index} className="gutter-line">
                        {index + 1}
                    </div>
                ))}
            </div>

            {/* 編輯與高亮工作區 */}
            <div className="editor-workspace">
                <pre 
                    className="editor-highlight-overlay" 
                    ref={overlayRef}
                    style={{ fontSize: `${fontSize}px` }}
                    aria-hidden="true"
                >
                    <code 
                        className={`language-${language}`}
                        dangerouslySetInnerHTML={{ __html: highlighted }}
                    />
                </pre>
                <textarea
                    className="editor-textarea"
                    ref={textareaRef}
                    value={content}
                    onChange={(e) => onChange(e.target.value)}
                    onScroll={handleScroll}
                    spellCheck={false}
                    style={{ fontSize: `${fontSize}px` }}
                    placeholder="開始在這裡輸入文字或程式碼..."
                />
            </div>
        </div>
    );
};
