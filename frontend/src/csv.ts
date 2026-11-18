type CsvResult = { rows: string[][]; error?: string };

export function parseCsv(content: string): CsvResult {
    const rows: string[][] = [];
    let row: string[] = [];
    let field = '';
    let state: 'plain' | 'quoted' | 'closed' = 'plain';

    const invalid = (message: string): CsvResult => ({
        rows,
        error: `第 ${rows.length + 1} 筆、第 ${row.length + 1} 欄${message}`,
    });

    const start = content.startsWith('\uFEFF') ? 1 : 0;
    for (let i = start; i < content.length; i++) {
        const char = content[i];
        if (state === 'quoted') {
            if (char !== '"') {
                field += char;
            } else if (content[i + 1] === '"') {
                field += '"';
                i++;
            } else {
                state = 'closed';
            }
        } else if (char === ',' || char === '\r' || char === '\n') {
            row.push(field);
            field = '';
            state = 'plain';
            if (char !== ',') {
                rows.push(row);
                row = [];
                if (char === '\r' && content[i + 1] === '\n') i++;
            }
        } else if (state === 'closed') {
            return invalid('的結尾引號後只能接逗號或換行。');
        } else if (char === '"') {
            if (field.length > 0) return invalid('的引號必須放在欄位開頭。');
            state = 'quoted';
        } else {
            field += char;
        }
    }

    if (state === 'quoted') return invalid('缺少結尾引號。');
    if (row.length || field.length || state === 'closed') {
        row.push(field);
        rows.push(row);
    }
    return { rows };
}
