export interface SoftwareUpdate {
    version: string;
    date: string;
    changes: string[];
}

export const SOFTWARE_UPDATES: SoftwareUpdate[] = [
    {
        version: "v 0.5.0",
        date: "2026-03-29",
        changes: [
            "Migrate solver from python to rust",
            "Calculation time reduce from 100% to 10%",
            "minor bug fixes",
        ]
    },
    {
        version: "v 0.4.2",
        date: "2026-02-22",
        changes: [
            "add arc length control method",
            "fixed smoothing value for stress and displacement using shape function",
            "bug fixes"
        ]
    },
    {
        version: "v 0.4.1",
        date: "2026-02-18",
        changes: [
            "add strain output",
            "add Ux and Uy output",
            "bug fixes"
        ]
    },
    {
        version: "v 0.4.0",
        date: "2026-02-17",
        changes: [
            "add embeded beam",
            "add Gravity Loading for initial phase",
            "add reset displacement features",
            "bug fixes"
        ]
    },
    {
        version: "v 0.3.0",
        date: "2026-02-15",
        changes: [
            "add Hoek-Brown material model for rock",
            "staging analysis bug fix",
            "add sample projects",
            "hide grid feature"
        ]
    },
    {
        version: "v 0.2.5",
        date: "2026-02-13",
        changes: [
            "add dark/light theme mode",
            "UI Updates",
            "rate limit",
            "bug fixes",
        ]
    },
    {
        version: "v 0.2.4",
        date: "2026-02-11",
        changes: [
            "add water level override for each phase",
            "edit polygon points",
            "add documentation",
            "bug fixes",
        ]
    },
    {
        version: "v 0.2.3",
        date: "2026-02-03",
        changes: [
            "add material override for each phase",
            "hover value for displacement and stress",
            "smoothing value for stress and displacement",
            "bug fixes",
        ]
    },
    {
        version: "v 0.2.2",
        date: "2026-02-02",
        changes: [
            "add feedback input",
            "responsive design for mobile devices",
            "switch dark/light background color",
            "bug fixes"
        ]
    },
    {
        version: "v 0.2.1",
        date: "2026-02-01",
        changes: [
            "Improved solver performance and calculation time",
            "Updated calculation method from CST to T6 with 3 integration points for better accuracy",
            "Fixed issue with mesh generation for",
            "add excess pore water pressure to the solver",
            "add line load",
            "save and load projects directly from cloud",
            "add cloud save and load projects",
            "bug fixes"
        ]
    },
    {
        version: "v 0.1.0",
        date: "2026-01-31",
        changes: [
            "Initial Beta Release",
            "Geotechnical FEA Solver integration",
            "Import DXF support",
            "Added Mesh and Staging workflows",
            "Advanced result visualization"
        ]
    },
    {
        version: "v 0.0.9",
        date: "2026-01-15",
        changes: [
            "Internal testing phase",
            "Bug fixes in solver core",
            "UI improvements for Input panel"
        ]
    }
];
