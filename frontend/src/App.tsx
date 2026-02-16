import { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import { DocumentationLayout } from './docs/DocumentationLayout';
import { Introduction } from './docs/Introduction';
import { UserManual } from './docs/UserManual';
import { ScientificReference } from './docs/ScientificReference';
import { InputCanvas } from './component/InputCanvas';
import { OutputCanvas } from './component/OutputCanvas';
import { AppHeader } from './component/AppHeader';
import { WizardNavigation, WizardTab } from './component/WizardNavigation';
import { InputToolbar } from './component/InputToolbar';

import { InputSidebar } from './component/InputSidebar';
import { MeshSidebar } from './component/MeshSidebar';
import { StagingSidebar } from './component/StagingSidebar';
import { ResultSidebar } from './component/ResultSidebar';
import { DEFAULT_PHASES, SAMPLE_SOLVER_SETTINGS, SAMPLE_GENERAL_SETTINGS, SAMPLE_MESH_SETTINGS } from './sample_data';
import { SampleManifest } from './data/samples';
import { api, ApiError } from './api';
import { MeshResponse, SolverResponse, PhaseRequest, Material, PolygonData, PointLoad, LineLoad, GeneralSettings, SolverSettings, MeshSettings, StepPoint, ProjectFile, ProjectMetadata, PhaseType, WaterLevel, EmbeddedBeam, EmbeddedBeamMaterial } from './types';
import { MaterialModal } from './component/MaterialModal';
import { EmbeddedBeamMaterialModal } from './component/EmbeddedBeamMaterialModal';
import { SettingsModal } from './component/SettingsModal';
import { CloudLoadModal } from './component/CloudLoadModal';
import { FeedbackModal } from './component/FeedbackModal';
import { SampleGalleryModal } from './component/SampleGalleryModal';
import { propagateMaterialChanges } from './utils/materialUtils';
import { APP_VERSION } from './version';
import { AuthProvider, useAuth } from './context/AuthContext';
import { pb } from './pb';
import { AuthModal } from './component/AuthModal';
import { AlertModal, AlertType } from './component/AlertModal';
import { ConfirmModal } from './component/ConfirmModal';
import { parseDXF } from './utils/dxfImport';
import { PanelLeftClose } from 'lucide-react';

function MainApp() {
    const { isValid, user } = useAuth();
    // 0. Project State
    const [projectName, setProjectName] = useState("New Project");
    const [cloudProjectId, setCloudProjectId] = useState<string | null>(null);
    const [isCloudModalOpen, setIsCloudModalOpen] = useState(false);
    const [isCloudSaving, setIsCloudSaving] = useState(false);

    // 1. Wizard State
    const [activeTab, setActiveTab] = useState<WizardTab>(WizardTab.INPUT);
    const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
    const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);
    const [isSampleGalleryOpen, setIsSampleGalleryOpen] = useState(false);

    // 2. Data State
    const [materials, setMaterials] = useState<Material[]>([]);
    const [beamMaterials, setBeamMaterials] = useState<EmbeddedBeamMaterial[]>([]); // NEW
    const [polygons, setPolygons] = useState<PolygonData[]>([]);
    const [pointLoads, setPointLoads] = useState<PointLoad[]>([]);
    const [lineLoads, setLineLoads] = useState<LineLoad[]>([]);
    const [embeddedBeams, setEmbeddedBeams] = useState<EmbeddedBeam[]>([]); // NEW
    const [waterLevels, setWaterLevels] = useState<WaterLevel[]>([]); // NEW
    const [phases, setPhases] = useState<PhaseRequest[]>(DEFAULT_PHASES);
    const [generalSettings, setGeneralSettings] = useState<GeneralSettings>(SAMPLE_GENERAL_SETTINGS);
    const [solverSettings, setSolverSettings] = useState<SolverSettings>(SAMPLE_SOLVER_SETTINGS);
    const [meshSettings, setMeshSettings] = useState<MeshSettings>(SAMPLE_MESH_SETTINGS);

    // 3. Execution State
    const [meshResponse, setMeshResponse] = useState<MeshResponse | null>(null);
    const [solverResponse, setSolverResponse] = useState<SolverResponse | null>(null);
    const [isGeneratingMesh, setIsGeneratingMesh] = useState(false);
    const [isRunningAnalysis, setIsRunningAnalysis] = useState(false);
    const [abortController, setAbortController] = useState<AbortController | null>(null);
    const [currentPhaseIdx, setCurrentPhaseIdx] = useState(0);
    const [liveStepPoints, setLiveStepPoints] = useState<StepPoint[]>([]);
    const [editingMaterial, setEditingMaterial] = useState<Material | null>(null);
    const [editingBeamMaterial, setEditingBeamMaterial] = useState<EmbeddedBeamMaterial | null>(null); // NEW
    const [drawMode, setDrawMode] = useState<string | null>(null);
    const [selectedEntity, setSelectedEntity] = useState<{ type: string, id: string | number } | null>(null);

    // 4. Alert Modal State
    const [alertConfig, setAlertConfig] = useState<{
        isOpen: boolean;
        title: string;
        message: string;
        type: AlertType;
    }>({
        isOpen: false,
        title: '',
        message: '',
        type: 'info'
    });

    const showAlert = (title: string, message: string, type: AlertType = 'info') => {
        setAlertConfig({ isOpen: true, title, message, type });
    };

    // 5. Confirm Modal State
    const [confirmConfig, setConfirmConfig] = useState<{
        isOpen: boolean;
        title: string;
        message: string;
        onConfirm: () => void;
        isDestructive: boolean;
        confirmText?: string;
    }>({
        isOpen: false,
        title: '',
        message: '',
        onConfirm: () => { },
        isDestructive: false
    });

    const showConfirm = (title: string, message: string, onConfirm: () => void, isDestructive: boolean = false, confirmText?: string) => {
        setConfirmConfig({ isOpen: true, title, message, onConfirm, isDestructive, confirmText });
    };

    // 6. Handlers
    const handleImportDXF = async (file: File) => {
        try {
            const importedPolygons = await parseDXF(file);
            if (importedPolygons.length > 0) {
                const materialId = materials[0]?.id || 'default';
                const polygonsWithMaterial = importedPolygons.map(p => ({
                    ...p,
                    materialId
                }));
                setPolygons([...polygons, ...polygonsWithMaterial]);
                showAlert("Import Success", `Successfully imported ${importedPolygons.length} polygons.`, 'success');
            } else {
                showAlert("Import Warning", "No closed polygons or regions found in DXF.", 'warning');
            }
        } catch (error) {
            console.error("Import failed:", error);
            showAlert("Import Error", "Failed to import DXF file. See console for details.", 'error');
        }
    };

    const handleSaveMaterial = (mat: Material) => {
        setMaterials(materials.map(m => m.id === mat.id ? mat : m));
        setEditingMaterial(null);
    };

    const handleGenerateMesh = async () => {
        setIsGeneratingMesh(true);
        setSolverResponse(null);  // Clear previous solver results
        try {
            const result = await api.generateMesh({
                polygons,
                materials,
                pointLoads,
                lineLoads,
                // water_level removed
                water_levels: waterLevels,
                embedded_beams: embeddedBeams,
                mesh_settings: meshSettings
            });
            setMeshResponse(result);
            if (result.success) {
                setActiveTab(WizardTab.MESH);
            } else {
                showAlert("Mesh Generation Failed", result.error || "Unknown error", 'error');
            }
        } catch (error: any) {
            console.error(error);
            if (error instanceof ApiError) {
                showAlert(error.title, error.description, 'error');
            } else {
                showAlert("Mesh Generation Error", error.message || "Unknown error", 'error');
            }
        } finally {
            setIsGeneratingMesh(false);
        }
    };

    const handleRunAnalysis = async () => {
        if (!meshResponse || !meshResponse.success) {
            showAlert("Missing Data", "Please generate mesh first!", 'warning');
            setActiveTab(WizardTab.MESH);
            return;
        }

        setIsRunningAnalysis(true);

        const controller = new AbortController();
        setAbortController(controller);

        try {
            const response = await api.solve({
                mesh: meshResponse,
                settings: solverSettings as any,
                phases: phases,
                // water_level removed
                water_levels: waterLevels, // NEW
                point_loads: pointLoads,
                line_loads: lineLoads,
                materials: materials,
                embedded_beams: embeddedBeams,
                beam_materials: beamMaterials
            }, controller.signal);

            if (!response.ok) {
                let errorTitle = "Analysis failed to start";
                let errorDesc = "An unexpected error occurred.";

                try {
                    const errorData = await response.json();
                    if (errorData && errorData.detail && typeof errorData.detail === 'object') {
                        errorTitle = errorData.detail.title;
                        errorDesc = errorData.detail.description;
                    } else if (errorData && typeof errorData.detail === 'string') {
                        errorDesc = errorData.detail;
                    }
                } catch (e) {
                    errorDesc = response.statusText;
                }

                showAlert(errorTitle, errorDesc, 'error');
                return;
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let accumulatedLog: string[] = [];
            let accumulatedPhases: any[] = [];
            let buffer = '';

            setSolverResponse({ success: false, phases: [], log: [] });
            setLiveStepPoints([]);

            while (true) {
                const { done, value } = await reader?.read()!;
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const update = JSON.parse(line);
                        if (update.type === 'log') {
                            accumulatedLog.push(update.content);
                            setSolverResponse(prev => prev ? { ...prev, log: [...accumulatedLog] } : { success: false, phases: [], log: [update.content] });
                        } else if (update.type === 'phase_result') {
                            setLiveStepPoints([]);
                            accumulatedPhases.push(update.content);
                            setSolverResponse(prev => prev ? {
                                ...prev,
                                phases: [...accumulatedPhases],
                            } : null);
                            setCurrentPhaseIdx(accumulatedPhases.length - 1);
                        } else if (update.type === 'step_point') {
                            setLiveStepPoints(prev => [...prev, update.content]);
                        } else if (update.type === 'final') {
                            setSolverResponse(update.content);
                        }
                    } catch (e) {
                        console.error("Stream parse error", e);
                    }
                }
            }
        } catch (error: any) {
            if (error.name === 'AbortError') {
                console.log("Analysis aborted.");
            } else {
                console.error(error);
                showAlert("Analysis Failed", "Analysis failed to complete.", 'error');
            }
        } finally {
            setIsRunningAnalysis(false);
            setAbortController(null);
        }
    };

    const handleCancelAnalysis = () => {
        if (abortController) {
            abortController.abort();
        }
    };

    const handleAddPolygon = (vertices: { x: number, y: number }[]) => {
        const newPoly: PolygonData = {
            vertices,
            materialId: materials[0]?.id || 'default'
        };
        setPolygons([...polygons, newPoly]);
        setDrawMode(null);
    };

    const handleUpdatePolygon = (idx: number, data: Partial<PolygonData>) => {
        const newPolys = [...polygons];
        newPolys[idx] = { ...newPolys[idx], ...data };
        setPolygons(newPolys);
    };

    const handleUpdatePolygonPoints = (idx: number, points: { x: number, y: number }[]) => {
        handleUpdatePolygon(idx, { vertices: points });
    };

    const handleAddPointLoad = (x: number, y: number) => {
        const newLoad: PointLoad = {
            id: `load_${Date.now()}`,
            x, y,
            fx: 0,
            fy: -100 // Default downward load
        };
        setPointLoads([...pointLoads, newLoad]);
        setDrawMode(null);
    };

    const handleAddLineLoad = (x1: number, y1: number, x2: number, y2: number) => {
        const newLoad: LineLoad = {
            id: `line_load_${Date.now()}`,
            x1, y1, x2, y2,
            fx: 0,
            fy: -10 // Default downward distributed load
        };
        setLineLoads([...lineLoads, newLoad]);
        setDrawMode(null);
    };

    const handleAddWaterLevel = (points: { x: number, y: number }[]) => {
        const newWL: WaterLevel = {
            id: `wl_${Date.now()}`,
            name: `Water Level ${waterLevels.length + 1}`,
            points
        };
        setWaterLevels([...waterLevels, newWL]);
    };

    const handleAddEmbeddedBeam = (points: { x: number, y: number }[]) => {
        const id = `ebr_${Date.now()}`;
        const newBeam: EmbeddedBeam = {
            id,
            points,
            materialId: beamMaterials.length > 0 ? beamMaterials[0].id : ''
        };
        setEmbeddedBeams([...embeddedBeams, newBeam]);

        // Auto-activate in current phase
        const newPhases = [...phases];
        if (newPhases[currentPhaseIdx]) {
            const ph = { ...newPhases[currentPhaseIdx] };
            ph.active_beam_ids = [...(ph.active_beam_ids || []), id];
            newPhases[currentPhaseIdx] = ph;
            setPhases(newPhases);
        }

        setDrawMode(null);
    };

    const handleDeleteMaterial = (id: string) => {
        setMaterials(materials.filter(m => m.id !== id));
        if (selectedEntity?.type === 'material' && selectedEntity.id === id) setSelectedEntity(null);
    };

    const handleDeletePolygon = (idx: number) => {
        setPolygons(polygons.filter((_, i) => i !== idx));
        if (selectedEntity?.type === 'polygon' && selectedEntity.id === idx) setSelectedEntity(null);
    };

    const handleDeleteLoad = (id: string) => {
        setPointLoads(pointLoads.filter(l => l.id !== id));
        setLineLoads(lineLoads.filter(l => l.id !== id));
        if (selectedEntity?.type === 'load' && selectedEntity.id === id) setSelectedEntity(null);
    };

    const handleDeleteWaterPoint = (wlIndex: number, ptIndex: number) => {
        console.log(`Deleting water point ${ptIndex} from level ${wlIndex}`);
        const next = [...waterLevels];
        if (next[wlIndex]) {
            next[wlIndex] = {
                ...next[wlIndex],
                points: next[wlIndex].points.filter((_, i) => i !== ptIndex)
            };
            setWaterLevels(next);
        }
    };

    const handleDeleteWaterLevel = (id: string) => {
        showConfirm(
            "Delete Water Level",
            "Are you sure you want to delete this water level?",
            () => {
                console.log(`Deleting water level ${id}`);
                setWaterLevels(waterLevels.filter(wl => wl.id !== id));
                if (selectedEntity?.type === 'water_level' && selectedEntity.id === id) setSelectedEntity(null);
                setConfirmConfig(prev => ({ ...prev, isOpen: false }));
            },
            true,
            "Delete"
        );
    };

    const handleUpdateWaterLevel = (index: number, newWL: WaterLevel) => {
        const next = [...waterLevels];
        next[index] = newWL;
        setWaterLevels(next);
    };

    const handleDeleteBeamMaterial = (id: string) => {
        setBeamMaterials(beamMaterials.filter(m => m.id !== id));
        if (selectedEntity?.type === 'beamMaterial' && selectedEntity.id === id) setSelectedEntity(null);
        // Clear from beams using it
        setEmbeddedBeams(embeddedBeams.map(b => b.materialId === id ? { ...b, materialId: '' } : b));
    };

    const handleDeleteEmbeddedBeam = (id: string) => {
        setEmbeddedBeams(embeddedBeams.filter(b => b.id !== id));
        if (selectedEntity?.type === 'embeddedBeam' && selectedEntity.id === id) setSelectedEntity(null);
        // Clear from phases
        setPhases(phases.map(p => ({
            ...p,
            active_beam_ids: p.active_beam_ids?.filter(bid => bid !== id) || []
        })));
    };

    const handleSaveProject = () => {
        const metadata: ProjectMetadata = {
            lastEdited: new Date().toISOString(),
            authorName: user?.name,
            authorEmail: user?.email,
        };

        const projectData: ProjectFile = {
            version: APP_VERSION,
            projectName,
            metadata,
            materials,
            beamMaterials, // NEW
            polygons,
            pointLoads,
            lineLoads,
            waterLevel: waterLevels.length > 0 ? waterLevels[0].points : [],
            waterLevels,
            embeddedBeams, // NEW
            phases,
            generalSettings,
            solverSettings,
            meshSettings,
            meshResponse
            // solverResponse excluded for smaller file size
        };

        const blob = new Blob([JSON.stringify(projectData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${projectName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.tsm`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handleLoadProject = (file: File) => {
        showConfirm(
            "Load Project",
            "Loading a project will replace all current data. Are you sure you want to continue?",
            () => {
                setConfirmConfig(prev => ({ ...prev, isOpen: false }));
                const reader = new FileReader();
                reader.onload = (e) => {
                    try {
                        const projectFile: ProjectFile = JSON.parse(e.target?.result as string);
                        setMaterials(projectFile.materials || []);
                        setBeamMaterials(projectFile.beamMaterials || []); // NEW
                        setPolygons(projectFile.polygons || []);
                        setPointLoads(projectFile.pointLoads || []);
                        setLineLoads(projectFile.lineLoads || []);
                        setWaterLevels(projectFile.waterLevels || []);
                        setEmbeddedBeams(projectFile.embeddedBeams || []); // NEW
                        setPhases(projectFile.phases || []);
                        setGeneralSettings(projectFile.generalSettings || SAMPLE_GENERAL_SETTINGS);
                        setSolverSettings(projectFile.solverSettings || SAMPLE_SOLVER_SETTINGS);
                        setMeshSettings(projectFile.meshSettings || SAMPLE_MESH_SETTINGS);
                        setProjectName(projectFile.projectName || "Untitled Project");
                        setCloudProjectId(null); // Reset cloud ID for local load

                        // Switch to input tab after load
                        // Explicitly clear results for a fresh start
                        setMeshResponse(null);
                        setSolverResponse(null);
                        setActiveTab(WizardTab.INPUT);

                        showAlert("Project Load Success", "Project loaded successfully!", 'success');
                    } catch (err) {
                        console.error("Failed to load project:", err);
                        showAlert("Project Load Error", "Failed to load project file. Invalid format.", 'error');
                    }
                };
                reader.readAsText(file);
            }
        );
    };

    const handleNewProject = () => {
        showConfirm(
            "Create New Project",
            "This will clear all current data and start a fresh project. Any unsaved changes will be lost. Are you sure?",
            () => {
                setConfirmConfig(prev => ({ ...prev, isOpen: false }));

                // Reset to initial state
                // materials
                setMaterials([]);
                setBeamMaterials([]);
                // polygons
                setPolygons([]);
                // loads
                setPointLoads([]);
                setLineLoads([]);
                setWaterLevels([]);
                // embedded beams
                setEmbeddedBeams([]);
                // phases
                setPhases(DEFAULT_PHASES);
                // settings
                setGeneralSettings(SAMPLE_GENERAL_SETTINGS);
                setSolverSettings(SAMPLE_SOLVER_SETTINGS);
                setMeshSettings(SAMPLE_MESH_SETTINGS);

                setProjectName("New Project");
                setCloudProjectId(null);

                setMeshResponse(null);
                setSolverResponse(null);
                setIsGeneratingMesh(false);
                setIsRunningAnalysis(false);
                setLiveStepPoints([]);
                setEditingMaterial(null);
                setDrawMode(null);
                setSelectedEntity(null);

                setActiveTab(WizardTab.INPUT);

                showAlert("New Project", "Started a new project successfully.", 'success');
            },
            true, // Is Destructive
            "Create New"
        );
    };

    const handleCloudSave = async (asNew: boolean = false) => {
        if (!user) {
            showAlert("Login Required", "Please login to save to cloud.", 'warning');
            return;
        }

        const metadata: ProjectMetadata = {
            lastEdited: new Date().toISOString(),
            authorName: user.name,
            authorEmail: user.email
        };

        const projectData: ProjectFile = {
            version: APP_VERSION,
            projectName,
            metadata,
            materials,
            polygons,
            pointLoads,
            lineLoads,
            waterLevel: waterLevels.length > 0 ? waterLevels[0].points : [],
            waterLevels,
            beamMaterials,
            embeddedBeams,
            phases,
            generalSettings,
            solverSettings,
            meshSettings,
            meshResponse
            // solverResponse excluded for smaller file size
        };

        try {
            setIsCloudSaving(true);
            if (cloudProjectId && !asNew) {
                // Update existing
                await pb.collection('terrasim_projects').update(cloudProjectId, {
                    name: projectName,
                    data: projectData
                });
                showAlert("Cloud Save Success", "Project saved to cloud successfully!", 'success');
            } else {
                // Create new
                const record = await pb.collection('terrasim_projects').create({
                    user: user.id, // Assuming relation field is named 'user'
                    name: projectName,
                    data: projectData,
                    version: APP_VERSION
                });
                setCloudProjectId(record.id);
                showAlert("Cloud Success", asNew ? "Project saved as new copy on cloud!" : "Project created on cloud successfully!", 'success');
            }
        } catch (error) {
            console.error("Cloud save failed:", error);
            showAlert("Cloud Save Error", "Failed to save project to cloud.", 'error');
        } finally {
            setIsCloudSaving(false);
        }
    };

    const handleCloudLoad = () => {
        setIsCloudModalOpen(true);
    };

    const handleLoadFromCloudData = (projectData: ProjectFile, recordId: string) => {
        showConfirm(
            "Load Cloud Project",
            "Loading a project will replace all current data. Are you sure you want to continue?",
            () => {
                setConfirmConfig(prev => ({ ...prev, isOpen: false }));
                try {
                    setMaterials(projectData.materials || []);
                    setBeamMaterials(projectData.beamMaterials || []); // NEW
                    setPolygons(projectData.polygons || []);
                    setPointLoads(projectData.pointLoads || []);
                    setLineLoads(projectData.lineLoads || []);
                    setWaterLevels(projectData.waterLevels || []);
                    setEmbeddedBeams(projectData.embeddedBeams || []); // NEW
                    setPhases(projectData.phases || []);
                    setGeneralSettings(projectData.generalSettings || SAMPLE_GENERAL_SETTINGS);
                    setSolverSettings(projectData.solverSettings || SAMPLE_SOLVER_SETTINGS);
                    setMeshSettings(projectData.meshSettings || SAMPLE_MESH_SETTINGS);
                    setProjectName(projectData.projectName || "Untitled Project");
                    setCloudProjectId(recordId);

                    // Explicitly clear results for a fresh start
                    setMeshResponse(null);
                    setSolverResponse(null);
                    setActiveTab(WizardTab.INPUT);
                } catch (err) {
                    console.error("Failed to load project:", err);
                    showAlert("Cloud Load Error", "Failed to load project data.", 'error');
                }
            }
        );
    };

    const handleLoadSample = (sampleProps: SampleManifest) => {
        showConfirm(
            "Load Sample Project",
            `Loading "${sampleProps.name}" will replace current data. Are you sure?`,
            () => {
                setConfirmConfig(prev => ({ ...prev, isOpen: false }));
                setIsSampleGalleryOpen(false); // Close gallery

                const sample = sampleProps.data;
                setMaterials(sample.materials);
                setBeamMaterials(sample.beamMaterials || []); // NEW
                setPolygons(sample.polygons);
                setPointLoads(sample.pointLoads);
                setLineLoads(sample.lineLoads || []);
                setWaterLevels(sample.waterLevels || []);
                setEmbeddedBeams(sample.embeddedBeams || []); // NEW
                setPhases(sample.phases);
                setGeneralSettings(sample.generalSettings || SAMPLE_GENERAL_SETTINGS);
                setSolverSettings(sample.solverSettings || SAMPLE_SOLVER_SETTINGS);
                setMeshSettings(sample.meshSettings || SAMPLE_MESH_SETTINGS);
                setProjectName(sample.name);

                setCloudProjectId(null);
                setMeshResponse(null);
                setSolverResponse(null);
                setActiveTab(WizardTab.INPUT);

                showAlert("Sample Loaded", `"${sampleProps.name}" loaded successfully.`, 'success');
            }
        );
    };

    const handleToggleActive = (type: 'polygon' | 'load' | 'embeddedBeam', id: string | number) => {
        const newPhases = [...phases];
        const phase = { ...newPhases[currentPhaseIdx] }; // Shallow copy phase object

        if (!phase.active_polygon_indices) phase.active_polygon_indices = polygons.map((_, i) => i);
        if (!phase.active_load_ids) {
            phase.active_load_ids = [...pointLoads.map(l => l.id), ...lineLoads.map(l => l.id)];
        }
        if (!phase.active_beam_ids) {
            phase.active_beam_ids = embeddedBeams.map(b => b.id);
        }

        if (type === 'polygon') {
            const idx = id as number;
            // Capture old state for propagation
            const oldCurrentMat = { ...phase.current_material };
            const nextCurrentMat = { ...phase.current_material };

            if (phase.active_polygon_indices.includes(idx)) {
                phase.active_polygon_indices = phase.active_polygon_indices.filter(i => i !== idx);
                delete nextCurrentMat[idx]; // Sync material state
            } else {
                phase.active_polygon_indices = [...phase.active_polygon_indices, idx];
                // Sync material state: Default to inheriting or base
                if (phase.parent_material && phase.parent_material[idx]) {
                    nextCurrentMat[idx] = phase.parent_material[idx];
                } else if (polygons[idx]) {
                    nextCurrentMat[idx] = polygons[idx].materialId;
                }
            }
            phase.current_material = nextCurrentMat;

            // Assign back before propagation
            newPhases[currentPhaseIdx] = phase;


            // Propagate material changes
            propagateMaterialChanges(newPhases, phase.id, oldCurrentMat, polygons);

        } else if (type === 'embeddedBeam') {
            const beamId = id as string;
            // Ensure array exists
            const currentIds = phase.active_beam_ids || [];

            if (currentIds.includes(beamId)) {
                phase.active_beam_ids = currentIds.filter(bid => bid !== beamId);
            } else {
                phase.active_beam_ids = [...currentIds, beamId];
            }
            newPhases[currentPhaseIdx] = phase;
        } else {
            const loadId = id as string;
            if (phase.active_load_ids.includes(loadId)) {
                phase.active_load_ids = phase.active_load_ids.filter(lid => lid !== loadId);
            } else {
                phase.active_load_ids = [...phase.active_load_ids, loadId];
            }
            newPhases[currentPhaseIdx] = phase;
        }

        // Keep existing Safety propagation for active set
        const propagateSafety = (pts: PhaseRequest[], parentId: string, activePolygons: number[], activeLoads: string[]) => {
            pts.forEach((ph, i) => {
                if (ph.parent_id === parentId && ph.phase_type === PhaseType.SAFETY_ANALYSIS) {
                    pts[i] = {
                        ...ph,
                        active_polygon_indices: [...activePolygons],
                        active_load_ids: [...activeLoads]
                    };
                    propagateSafety(pts, ph.id, activePolygons, activeLoads);
                }
            });
        };

        propagateSafety(newPhases, phase.id, phase.active_polygon_indices, phase.active_load_ids);

        setPhases(newPhases);
    };
    const handleOverrideMaterial = (polyIdx: number, matId: string) => {
        const newPhases = [...phases];
        const phase = { ...newPhases[currentPhaseIdx] };

        // Capture old state
        const oldCurrentMat = { ...phase.current_material };

        // Update current_material for this polygon
        phase.current_material = { ...phase.current_material, [polyIdx]: matId };

        newPhases[currentPhaseIdx] = phase;

        // Propagate to ALL child phases using shared utility
        propagateMaterialChanges(newPhases, phase.id, oldCurrentMat, polygons);

        setPhases(newPhases);
    };

    const currentPhase = phases[currentPhaseIdx];
    const [inputSideBarOpen, setInputSideBarOpen] = useState(false);
    const [meshSideBarOpen, setMeshSideBarOpen] = useState(false);
    const [stagingSideBarOpen, setStagingSideBarOpen] = useState(false);
    const [resultSideBarOpen, setResultSideBarOpen] = useState(false);
    const isWindowSizeSmall = window.innerWidth < 768;
    const isInputTab = activeTab === WizardTab.INPUT || activeTab === WizardTab.MESH || activeTab === WizardTab.STAGING;

    return (
        <div className="flex flex-col h-screen overflow-hidden bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 selection:bg-blue-500/30">
            {!isValid && <AuthModal />}
            {isSampleGalleryOpen && (
                <SampleGalleryModal
                    onClose={() => setIsSampleGalleryOpen(false)}
                    onLoad={handleLoadSample}
                />
            )}

            <AppHeader
                projectName={projectName}
                setProjectName={setProjectName}
                onOpenSettings={() => setIsSettingsModalOpen(true)}
                onSaveProject={handleSaveProject}
                onLoadProject={handleLoadProject}
                onCloudSave={() => handleCloudSave(false)}
                onCloudSaveAsNew={() => handleCloudSave(true)}
                onNewProject={handleNewProject}
                onOpenSampleGallery={() => setIsSampleGalleryOpen(true)}
                onCloudLoad={handleCloudLoad}
                onOpenFeedback={() => setIsFeedbackModalOpen(true)}
                isCloudSaving={isCloudSaving}
            />

            <div className="flex-1 flex overflow-hidden relative">

                {isInputTab && (
                    <div className="flex h-full z-10 md:w-[400px] w-0">
                        {activeTab === WizardTab.INPUT && (
                            <>
                                <InputToolbar
                                    drawMode={drawMode}
                                    onDrawModeChange={setDrawMode}
                                    onImportDXF={handleImportDXF}
                                />
                                <div className={`md:hidden block absolute top-1 w-10 p-2 z-10 h-full  ${inputSideBarOpen ? 'translate-x-[calc(100vw-40px)] dark:bg-slate-900 bg-slate-100' : 'translate-x-0'} transition`}>
                                    <button onClick={() => setInputSideBarOpen(!inputSideBarOpen)}>
                                        <PanelLeftClose className={`w-6 h-6 ${inputSideBarOpen ? 'rotate-180' : ''}`} />
                                    </button>
                                </div>
                                {isWindowSizeSmall && (
                                    <div className={`absolute top-0 left-0 z-10 ${inputSideBarOpen ? 'translate-x-0' : '-translate-x-[calc(100vw-32px)]'} transition`}>
                                        <InputSidebar
                                            materials={materials}
                                            beamMaterials={beamMaterials} // NEW
                                            polygons={polygons}
                                            pointLoads={pointLoads}
                                            lineLoads={lineLoads}
                                            embeddedBeams={embeddedBeams} // NEW
                                            waterLevels={waterLevels} // NEW
                                            onUpdateMaterials={setMaterials}
                                            onUpdateBeamMaterials={setBeamMaterials} // NEW
                                            onUpdatePolygons={setPolygons}
                                            onUpdateLoads={setPointLoads}
                                            onUpdateLineLoads={setLineLoads}
                                            onUpdateEmbeddedBeams={setEmbeddedBeams} // NEW
                                            onAddWaterLevel={handleAddWaterLevel} // NEW
                                            onUpdateWaterLevel={handleUpdateWaterLevel} // NEW
                                            onDeleteWaterPoint={handleDeleteWaterPoint} // NEW
                                            onUpdatePolygonPoints={handleUpdatePolygonPoints}
                                            onEditMaterial={setEditingMaterial}
                                            onEditBeamMaterial={(mat) => setEditingBeamMaterial(mat)} // NEW
                                            onDeleteMaterial={handleDeleteMaterial}
                                            onDeleteBeamMaterial={handleDeleteBeamMaterial} // NEW
                                            onDeletePolygon={handleDeletePolygon}
                                            onDeleteLoad={handleDeleteLoad}
                                            onDeleteLineLoad={handleDeleteLoad}
                                            onDeleteEmbeddedBeam={handleDeleteEmbeddedBeam} // NEW
                                            onDeleteWaterLevel={handleDeleteWaterLevel}
                                            selectedEntity={selectedEntity}
                                            onSelectEntity={setSelectedEntity}
                                        />
                                    </div>
                                )}
                                {!isWindowSizeSmall && (
                                    <InputSidebar
                                        materials={materials}
                                        beamMaterials={beamMaterials} // NEW
                                        polygons={polygons}
                                        pointLoads={pointLoads}
                                        lineLoads={lineLoads}
                                        embeddedBeams={embeddedBeams} // NEW
                                        waterLevels={waterLevels} // NEW
                                        onUpdateMaterials={setMaterials}
                                        onUpdateBeamMaterials={setBeamMaterials} // NEW
                                        onUpdatePolygons={setPolygons}
                                        onUpdateLoads={setPointLoads}
                                        onUpdateLineLoads={setLineLoads}
                                        onUpdateEmbeddedBeams={setEmbeddedBeams} // NEW
                                        onAddWaterLevel={handleAddWaterLevel} // NEW
                                        onUpdateWaterLevel={handleUpdateWaterLevel} // NEW
                                        onDeleteWaterPoint={handleDeleteWaterPoint} // NEW
                                        onUpdatePolygonPoints={handleUpdatePolygonPoints}
                                        onEditMaterial={setEditingMaterial}
                                        onEditBeamMaterial={(mat) => setEditingBeamMaterial(mat)} // NEW
                                        onDeleteMaterial={handleDeleteMaterial}
                                        onDeleteBeamMaterial={handleDeleteBeamMaterial} // NEW
                                        onDeletePolygon={handleDeletePolygon}
                                        onDeleteLoad={handleDeleteLoad}
                                        onDeleteLineLoad={handleDeleteLoad}
                                        onDeleteEmbeddedBeam={handleDeleteEmbeddedBeam} // NEW
                                        onDeleteWaterLevel={handleDeleteWaterLevel}
                                        selectedEntity={selectedEntity}
                                        onSelectEntity={setSelectedEntity}
                                    />
                                )}
                            </>
                        )}

                        {activeTab === WizardTab.MESH && (
                            <>
                                <div className={`md:hidden block absolute top-1 w-10 p-2 h-full ${meshSideBarOpen ? 'translate-x-[calc(100vw-40px)] dark:bg-slate-900 bg-slate-100' : 'translate-x-0'} transition`}>
                                    <button onClick={() => setMeshSideBarOpen(!meshSideBarOpen)}>
                                        <PanelLeftClose className={`w-6 h-6 ${meshSideBarOpen ? 'rotate-180' : ''}`} />
                                    </button>
                                </div>
                                {isWindowSizeSmall && (
                                    <div className={`absolute top-0 left-0 z-10 ${meshSideBarOpen ? 'translate-x-0' : '-translate-x-[calc(100vw-32px)]'} transition`}>
                                        <MeshSidebar
                                            mesh={meshResponse}
                                            isGenerating={isGeneratingMesh}
                                            onGenerate={handleGenerateMesh}
                                            meshSettings={meshSettings}
                                            onSettingsChange={setMeshSettings}
                                        />
                                    </div>
                                )}
                                {!isWindowSizeSmall && (
                                    <MeshSidebar
                                        mesh={meshResponse}
                                        isGenerating={isGeneratingMesh}
                                        onGenerate={handleGenerateMesh}
                                        meshSettings={meshSettings}
                                        onSettingsChange={setMeshSettings}
                                    />
                                )}
                            </>
                        )}

                        {activeTab === WizardTab.STAGING && (
                            <>
                                <div className={`md:hidden block absolute top-1 w-10 p-2 h-full ${stagingSideBarOpen ? 'translate-x-[calc(100vw-40px)] dark:bg-slate-900 bg-slate-100' : 'translate-x-0'} transition`}>
                                    <button onClick={() => setStagingSideBarOpen(!stagingSideBarOpen)}>
                                        <PanelLeftClose className={`w-6 h-6 ${stagingSideBarOpen ? 'rotate-180' : ''}`} />
                                    </button>
                                </div>
                                {isWindowSizeSmall && (
                                    <div className={`absolute top-0 left-0 z-10 ${stagingSideBarOpen ? 'translate-x-0' : '-translate-x-[calc(100vw-32px)]'} transition`}>
                                        <StagingSidebar
                                            phases={phases}
                                            currentPhaseIdx={currentPhaseIdx}
                                            polygons={polygons}
                                            pointLoads={pointLoads}
                                            lineLoads={lineLoads}
                                            embeddedBeams={embeddedBeams}
                                            waterLevels={waterLevels} // NEW
                                            onPhasesChange={setPhases}
                                            onSelectPhase={setCurrentPhaseIdx}
                                        />
                                    </div>
                                )}
                                {!isWindowSizeSmall && (
                                    <StagingSidebar
                                        phases={phases}
                                        currentPhaseIdx={currentPhaseIdx}
                                        polygons={polygons}
                                        pointLoads={pointLoads}
                                        lineLoads={lineLoads}
                                        embeddedBeams={embeddedBeams}
                                        waterLevels={waterLevels} // NEW
                                        onPhasesChange={setPhases}
                                        onSelectPhase={setCurrentPhaseIdx}
                                    />
                                )}
                            </>
                        )}
                    </div>
                )}
                <div className="flex-1 flex-col overflow-hidden bg-slate-50 dark:bg-slate-900 relative">

                    <WizardNavigation
                        activeTab={activeTab}
                        onTabChange={setActiveTab}
                    />

                    <div className="flex-1 h-[calc(100vh-100px)] relative bg-slate-50 dark:bg-slate-950 mx-2 mb-2 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
                        {activeTab === WizardTab.INPUT && (
                            <InputCanvas
                                polygons={polygons}
                                pointLoads={pointLoads}
                                lineLoads={lineLoads}
                                materials={materials}
                                water_levels={waterLevels} // NEW
                                drawMode={drawMode}
                                onAddPolygon={handleAddPolygon}
                                onAddPointLoad={handleAddPointLoad}
                                onAddLineLoad={handleAddLineLoad}
                                onAddWaterLevel={handleAddWaterLevel}
                                onAddEmbeddedBeam={handleAddEmbeddedBeam} // NEW
                                onCancelDraw={() => setDrawMode(null)}
                                selectedEntity={selectedEntity}
                                onSelectEntity={setSelectedEntity}
                                onDeletePolygon={handleDeletePolygon}
                                onDeleteLoad={handleDeleteLoad}
                                onDeleteWaterLevel={handleDeleteWaterLevel}
                                onUpdatePolygon={handleUpdatePolygon}
                                onUpdateWaterLevel={handleUpdateWaterLevel} // NEW
                                activeTab={activeTab}
                                currentPhaseType={currentPhase?.phase_type}
                                generalSettings={generalSettings}
                                embeddedBeams={embeddedBeams} // NEW
                                beamMaterials={beamMaterials} // NEW
                            />
                        )}

                        {activeTab === WizardTab.STAGING && (
                            <InputCanvas
                                polygons={polygons}
                                pointLoads={pointLoads}
                                lineLoads={lineLoads}
                                materials={materials}
                                water_levels={waterLevels} // NEW
                                activePolygonIndices={currentPhase?.active_polygon_indices}
                                activeLoadIds={currentPhase?.active_load_ids}
                                activeWaterLevelId={currentPhase?.active_water_level_id} // NEW
                                activeBeamIds={currentPhase?.active_beam_ids} // NEW
                                drawMode={null}
                                onAddPolygon={() => { }}
                                onAddPointLoad={() => { }}
                                onAddLineLoad={() => { }}
                                onAddWaterLevel={() => { }}
                                onCancelDraw={() => { }}
                                selectedEntity={null}
                                onSelectEntity={() => { }}
                                onDeletePolygon={() => { }}
                                onDeleteLoad={() => { }}
                                onDeleteWaterLevel={() => { }}
                                onToggleActive={handleToggleActive}
                                onUpdatePolygon={handleUpdatePolygon}
                                activeTab={activeTab}
                                currentPhaseType={currentPhase?.phase_type}
                                generalSettings={generalSettings}
                                currentMaterial={currentPhase?.current_material}
                                onOverrideMaterial={handleOverrideMaterial}
                                onUpdateWaterLevel={() => { }}
                                embeddedBeams={embeddedBeams} // NEW
                                beamMaterials={beamMaterials} // NEW
                            />
                        )}

                        {activeTab === WizardTab.MESH && (
                            <div className="w-full h-full flex items-center justify-center relative">
                                {meshResponse?.success ? (
                                    <OutputCanvas
                                        mesh={meshResponse}
                                        polygon={polygons}
                                        solverResult={null}
                                        currentPhaseIdx={0}
                                        phases={phases}
                                        showControls={false}
                                        ignorePhases={true}
                                        generalSettings={generalSettings}
                                        materials={materials}
                                        beamMaterials={beamMaterials}
                                    />
                                ) : (
                                    <div className="text-slate-500 text-sm animate-pulse">Click "Generate Mesh" to see the mesh</div>
                                )}
                            </div>
                        )}

                        {activeTab === WizardTab.RESULT && (
                            <div className="w-full h-full relative z-30">
                                <OutputCanvas
                                    mesh={meshResponse}
                                    polygon={polygons}
                                    solverResult={solverResponse}
                                    currentPhaseIdx={currentPhaseIdx}
                                    phases={phases}
                                    generalSettings={generalSettings}
                                    materials={materials}
                                    beamMaterials={beamMaterials}
                                />
                                <div className={`md:hidden flex items-start justify-center absolute top-0 right-0 w-12 p-2 h-full border-x dark:border-slate-700 border-slate-200 dark:bg-slate-900 bg-slate-100 z-48 ${resultSideBarOpen ? '-translate-x-[calc(100vw-60px)]' : 'translate-x-0'} transition`}>
                                    <button onClick={() => setResultSideBarOpen(!resultSideBarOpen)}>
                                        <PanelLeftClose className={`w-6 h-6 ${resultSideBarOpen ? '' : 'rotate-180'}`} />
                                    </button>
                                </div>
                                {isWindowSizeSmall && (
                                    <div className={`relative absolute top-0 right-0 w-full h-full z-44 ${resultSideBarOpen ? 'translate-x-0' : 'translate-x-[calc(100vw-32px)]'} transition`}>
                                        <ResultSidebar
                                            solverResult={solverResponse}
                                            isRunning={isRunningAnalysis}
                                            onRun={handleRunAnalysis}
                                            onCancel={handleCancelAnalysis}
                                            phases={phases}
                                            currentPhaseIdx={currentPhaseIdx}
                                            onSelectPhase={setCurrentPhaseIdx}
                                        />
                                    </div>
                                )}
                                {!isWindowSizeSmall && (
                                    <ResultSidebar
                                        solverResult={solverResponse}
                                        isRunning={isRunningAnalysis}
                                        onRun={handleRunAnalysis}
                                        onCancel={handleCancelAnalysis}
                                        phases={phases}
                                        currentPhaseIdx={currentPhaseIdx}
                                        onSelectPhase={setCurrentPhaseIdx}
                                        liveStepPoints={liveStepPoints}
                                    />
                                )}
                            </div>
                        )}
                    </div>
                </div>

            </div>

            {editingMaterial && (
                <MaterialModal
                    material={editingMaterial}
                    onSave={handleSaveMaterial}
                    onClose={() => setEditingMaterial(null)}
                />
            )}

            {editingBeamMaterial && (
                <EmbeddedBeamMaterialModal
                    material={editingBeamMaterial}
                    onSave={(updated) => {
                        setBeamMaterials(beamMaterials.map(m => m.id === updated.id ? updated : m));
                        setEditingBeamMaterial(null);
                    }}
                    onClose={() => setEditingBeamMaterial(null)}
                />
            )}

            {isSettingsModalOpen && (
                <SettingsModal
                    generalSettings={generalSettings}
                    solverSettings={solverSettings}
                    onSave={(g, s) => {
                        setGeneralSettings(g);
                        setSolverSettings(s);
                    }}
                    onClose={() => setIsSettingsModalOpen(false)}
                />
            )}

            {isCloudModalOpen && (
                <CloudLoadModal
                    onLoad={handleLoadFromCloudData}
                    onClose={() => setIsCloudModalOpen(false)}
                />
            )}

            {isFeedbackModalOpen && (
                <FeedbackModal
                    onClose={() => setIsFeedbackModalOpen(false)}
                />
            )}

            <AlertModal
                isOpen={alertConfig.isOpen}
                title={alertConfig.title}
                message={alertConfig.message}
                type={alertConfig.type}
                onClose={() => setAlertConfig({ ...alertConfig, isOpen: false })}
            />

            <ConfirmModal
                isOpen={confirmConfig.isOpen}
                title={confirmConfig.title}
                message={confirmConfig.message}
                isDestructive={confirmConfig.isDestructive}
                confirmText={confirmConfig.confirmText}
                onConfirm={confirmConfig.onConfirm}
                onCancel={() => setConfirmConfig({ ...confirmConfig, isOpen: false })}
            />

            <div className="md:block hidden fixed bottom-3 right-3 z-[100] items-center justify-center flex flex-col dark:bg-slate-900/90 bg-slate-100/90 backdrop-blur-md py-2 px-4 rounded-xl border dark:border-slate-700 border-slate-200 shadow-2xl text-slate-400 z-[20]">
                <div className="text-[10px] text-center">TerraSim v{APP_VERSION} (Beta) | Copyright © 2026</div>
                <div className="text-[10px] border-b pb-1 mb-1 dark:border-slate-700 border-slate-200 w-full text-center">Dahar Engineer | All rights reserved.</div>
                <div className="text-[8px] text-center">This software is still under development.</div>
                <div className="text-[8px] text-center">Please use it at your own risk.</div>
            </div>
        </div>
    );
}

export default function App() {
    return (
        <AuthProvider>
            <Routes>
                <Route path="/" element={<MainApp />} />
                <Route path="/docs" element={<DocumentationLayout />}>
                    <Route index element={<Navigate to="introduction" replace />} />
                    <Route path="introduction" element={<Introduction />} />
                    <Route path="user-manual" element={<UserManual />} />
                    <Route path="scientific-reference" element={<ScientificReference />} />
                </Route>
            </Routes>
        </AuthProvider>
    );
}
