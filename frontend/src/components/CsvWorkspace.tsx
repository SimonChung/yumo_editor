import { useMemo, useState } from 'react';
import { parseCsv } from '../csv';
import { PreviewWorkspace, type WorkspaceProps } from './PreviewWorkspace';
import './CsvWorkspace.css';

const rowsPerPage = 200;

function CsvPreview({ content }: { content: string }) {
    const { rows, error } = useMemo(() => parseCsv(content), [content]);
    const [page, setPage] = useState(1);
    if (error) return <p role="status">{error}</p>;
    if (!rows.length) return <p>CSV 檔案目前沒有資料。</p>;

    const pageCount = Math.max(1, Math.ceil((rows.length - 1) / rowsPerPage));
    const currentPage = Math.min(page, pageCount);
    const start = 1 + (currentPage - 1) * rowsPerPage;
    return (
        <>
            {pageCount > 1 && (
                <nav className="csv-pagination" aria-label="CSV 預覽分頁">
                    <button type="button" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>上一頁</button>
                    <span>第 {currentPage} / {pageCount} 頁</span>
                    <button type="button" disabled={currentPage === pageCount} onClick={() => setPage(currentPage + 1)}>下一頁</button>
                </nav>
            )}
            <table aria-label="CSV 表格預覽">
                <thead>
                    <tr>{rows[0].map((value, col) => <th scope="col" key={col}>{value}</th>)}</tr>
                </thead>
                <tbody>
                    {rows.slice(start, start + rowsPerPage).map((row, index) => (
                        <tr key={start + index}>
                            {row.map((value, col) => <td key={col}>{value}</td>)}
                        </tr>
                    ))}
                </tbody>
            </table>
        </>
    );
}

export function CsvWorkspace(props: WorkspaceProps) {
    return (
        <PreviewWorkspace {...props} format="CSV" language="plaintext">
            <CsvPreview content={props.content} />
        </PreviewWorkspace>
    );
}
