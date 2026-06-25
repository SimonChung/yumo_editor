export interface Tab {
    id: string;
    name: string;
    path: string;
    content: string;
    isDirty: boolean;
    encoding?: string;
}
