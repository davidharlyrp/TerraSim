import React from 'react';
import { Folder, Pen, Square, ArrowDown, ArrowDownToDot, ArrowDownToLine, ChartNoAxesColumnIncreasing, ChartNoAxesColumnDecreasing, TestTube } from 'lucide-react';

const Structure = {
    Input: {
        title: "1. Input Tab",
        desc: "Define the physical boundaries of your soil model. Draw polygons to represent different soil layers or structure and put load as an external load that would be applied to the model.",
        subtitle: [
            {
                title: "1.1 Geometry, Load & Structural Components",
                desc: "Define the physical boundaries of your soil model. Draw polygons to represent different soil layers or structure and put load as an external load that would be applied to the model.",
                items: [
                    "1.1.1 Geometry",
                    "1.1.2 Load",
                    "1.1.3 Structural Components"
                ]
            },
            {
                title: "1.2 Water Table",
                desc: "Water table is the boundary of the soil model that is in contact with the water.",
                items: [

                ]
            },
            {
                title: "1.3 Material Properties",
                desc: "Define the properties of material that will be applied on your geometry.",
                items: [
                    "1.3.1 Create Material",
                    "1.3.2 Assign Material"
                ]
            }
        ],
    },
    Mesh: {
        title: "2. Mesh Tab",
        desc: "Transition from continuous geometry to a discrete FEA model and create mesh for the geometry.",
        subtitle: [
            {
                title: "2.1 Mesh control Parameters",
                desc: "Setting the mesh parameters will control the quality and size of the mesh that will be generated.",
                items: [
                    "2.1.1 Mesh Size",
                    "2.1.2 Refinement"
                ]
            },
            {
                title: "2.2 Mesh Generation",
                desc: "Generate the mesh for the geometry.",
                items: []
            }
        ],
    },
    Staging: {
        title: "3. Staging Tab",
        desc: "Simulate real-world construction sequences like excavations, backfilling, or loading phases.",
        subtitle: [
            {
                title: "3.1 Phase Type",
                desc: "Define the type of phase that will be applied on your model.",
                items: [
                    "3.1.1 k0 Procedure",
                    // "3.1.2 Gravity Loading",
                    "3.1.2 Plastic Analysis",
                    "3.1.3 Safety Analysis"
                ]
            },
            {
                title: "3.2 Schema of Phases",
                desc: "Define the construction sequence and component state for each phase.",
                items: [
                    "3.2.1 Create Phase",
                    "3.2.2 Component Activation (Polygons, Loads, Structures)",
                    "3.2.3 Water Level Selection",
                    "3.2.4 Material Overrides"
                ]
            }
        ]
    },
    Results: {
        title: "4. Results Tab",
        desc: "Visualize the behavior of your model. Export detailed plots of displacements, stresses, and PWP distributions.",
        subtitle: [
            {
                title: "4.1 Running the Analysis",
                desc: "Execute the finite element calculation and monitor progress in real-time.",
                items: [
                    "4.1.1 Run/Cancel Analysis",
                    "4.1.2 Convergence Chart",
                    "4.1.3 Analysis Log"
                ]
            },
            {
                title: "4.2 Visualizing Results",
                desc: "Switch between several output views to inspect different physical quantities.",
                items: [
                    "4.2.1 Deformation (Mesh & Contour)",
                    "4.2.2 Stresses & PWP",
                    "4.2.3 Yield Status"
                ]
            },
            {
                title: "4.3 Interpretation & Summary",
                desc: "Quantitative summary and failure identification for the selected phase.",
                items: [
                    "4.3.1 Extrema Data",
                    "4.3.2 Yield Status Count",
                    "4.3.3 Failure Identification"
                ]
            }
        ]
    },
    Project: {
        title: "5. Project Management & Settings",
        desc: "Manage your project files and configure global application parameters to tailor the software to your needs.",
        subtitle: [
            {
                title: "5.1 Header Controls",
                desc: "Control global interaction from the top bar.",
                items: [
                    "5.1.1 Project Name",
                    "5.1.2 Feedback",
                    "5.1.3 Load Sample Project",
                    "5.1.4 Notifications & Updates",
                    "5.1.5 Documentation",
                    "5.1.6 Application Settings",
                    "5.1.7 Dark Mode",
                    "5.1.8 User Panel"
                ]
            },
            {
                title: "5.2 User Panel",
                desc: "Control your project files.",
                items: [
                    "5.2.1 New Project",
                    "5.2.2 Download Project",
                    "5.2.3 Save Project on Cloud",
                    "5.2.4 Save As new Project",
                    "5.2.5 Load Project from Cloud",
                    "5.2.6 Open Project",
                    "5.2.7 Log Out"
                ]
            },
            {
                title: "5.2 Application Settings",
                desc: "Configure visual and solver behaviors via the Global Settings modal.",
                items: [
                    "5.2.1 General Settings",
                    "5.2.2 Solver Settings"
                ]
            }
        ]
    }
}


const PhaseWrapper: React.FC<{ title: string; desc: string; children: React.ReactNode }> = ({ title, desc, children }) => (
    <div className="flex flex-col gap-12 group ">
        <div className="flex-1 space-y-4 py-2 border-b border-gray-500 ">
            <h2 className="text-2xl font-black text-white">{title}</h2>
            <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                {desc}
            </p>
        </div>
        {children}
    </div>
);

const Phase1Content = () => (
    <PhaseWrapper
        title={Structure.Input.title}
        desc={Structure.Input.desc}
    >
        <div className=''>
            {/* Geometry & Load */}
            <>
                <div className="flex-1 pl-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Input.subtitle[0].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Input.subtitle[0].desc}
                    </p>
                </div>
                <div className="flex flex-col pl-8 gap-4">
                    {/* Geometry */}
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Input.subtitle[0].items[0]}</h3>
                        <p className="description2">
                            We provide a simple and intuitive interface to draw polygons/rectangles and define the geometry of your soil model or structure as a cluster that you can use on the input tab.
                        </p>
                        <ul className="pl-6 space-y-2 list-disc list-outside">
                            <li className='font-semibold'> Create Polygon
                                <div>
                                    <p className='description2'>User can create polygon by using tools in the toolbar</p>
                                    <button
                                        title="Draw Polygon"
                                        className={`cursor-pointer w-10 relative py-2 px-2 my-4 text-sm text-white transition-all border h-full rounded-lg text-slate-400 border-white hover:text-slate-300`}
                                    >
                                        <Folder />
                                        <Pen className='absolute top-1 right-1 w-4 h-4' />
                                    </button>
                                    <p className='description2'>You can start create a polygon, and to create a polygon you need to click on the button and then click on the canvas to define the polygon point (minimum 3 points), to finish your polygon, user need to click on the first point or press enter on your keyboard.</p>
                                    <p className='description2'>To delete a polygon, you need to click on the polygon and then click left on your mouse that will be shown some option include delete, or you can press delete key on your keyboard.</p>
                                </div>
                            </li>
                            <li className='font-semibold'>Create Rectangle
                                <div>
                                    <p className='description2'>user can create rectangle by using tools in the toolbar</p>
                                    <button
                                        title="Draw Rectangle"
                                        className={`cursor-pointer w-10 relative py-2 px-2 my-4 text-sm text-white transition-all border h-full rounded-lg text-slate-400 border-white hover:text-slate-300`}
                                    >
                                        <Square />
                                        <Pen className='absolute top-1 right-1 w-4 h-4' />
                                    </button>
                                    <p className='description2'>You can start create a rectangle, and to create a rectangle you need to click on the button and then click on the canvas to define first corner of the rectangle and click on the canvas to define second corner of the rectangle.</p>
                                    <p className='description2'>You can delete a rectangle by using a same method as delete polygon.</p>
                                </div>
                            </li>

                            <li className='font-semibold'>Import from DXF
                                <div>
                                    <p className='description2'>We also provide user to import geometry from DXF file which can make user easier to create geometry</p>
                                    <button
                                        title="Import from DXF"
                                        className={`cursor-pointer w-10 relative py-2 px-2 my-4 text-sm text-white transition-all border h-full rounded-lg text-slate-400 border-white hover:text-slate-300`}
                                    >
                                        <Folder className="w-5 h-5" />
                                        <ArrowDown className="absolute bottom-0 left-0 right-0 m-auto w-4 h-4" />
                                    </button>
                                    <p className='description2'>
                                        To import geometry from DXF file, you need to click on the button and then choose the DXF file that you want to import.
                                        In this application, we only support DXF file that has only closed polyline that define the geometry, so keep in mind to make sure your geometry in DXF file is closed polyline and not region/line on any else.
                                    </p>
                                    <p className='description2'>
                                        For now we only user meter (m) unit to define length, distance, or coordinate of the geometry, so make sure that your geometry in DXF file is in meter unit.
                                    </p>
                                    <p className='description2'>
                                        After you choose the DXF file, the geometry will be imported and shown on the canvas directly.
                                    </p>
                                </div>
                            </li>
                        </ul>
                        <p className="description2">
                            Every geometry that you create will be shown on the canvas and you can still edit each of geometry point on sidebar.
                        </p>
                    </div>

                    {/* Load */}
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Input.subtitle[0].items[1]}</h3>
                        <p className="description2">
                            You can define the load that will be applied to the geometry that you have created as an external load.
                            TerraSim currently supports two types of static load, point load and distributed load.
                        </p>
                        <ul className="pl-6 space-y-2 list-disc list-outside">
                            <li className='font-semibold'>Point Load
                                <div>
                                    <p className='description2'>User can create point load by using tools in the toolbar. The point load is defined as a load that would be applied to a line load along 1 meter depth direction (z direction of the canvas) for plane strain.</p>
                                    <button
                                        title="Draw Point Load"
                                        className={`cursor-pointer w-10 relative py-2 px-2 my-4 text-sm text-white transition-all border h-full rounded-lg text-slate-400 border-white hover:text-slate-300`}
                                    >
                                        <div className="relative">
                                            <ArrowDownToDot />
                                            <Pen className='absolute -top-1 -right-1 w-3 h-3' />
                                        </div>
                                    </button>
                                    <p className='description2'>
                                        You can start create a point load, and to create a point load you need to click on the button and then click on the canvas to define where the point load point will be applied.
                                    </p>
                                    <p className='description2'>
                                        After you define where the point load point will be applied, it will be shown on the canvas and you can define the magnitude and for each direction of the point load on sidebar.
                                        For the magnitude of the point load, we only support KiloNewton per depth meter analysis (kN/m), and positive value (+) for x direction is directed to the right and positive value (+) for y direction is directed to the top of your model.
                                    </p>
                                </div>
                            </li>
                            <li className='font-semibold'>Distributed/Line Load
                                <div>
                                    <p className='description2'>User can create distributed load by using tools in the toolbar. For distributed line load, it will be applied along the line load direction and along 1 meter depth direction (z direction of the canvas) for plane strain.</p>
                                    <button
                                        title="Draw Distributed Load"
                                        className={`cursor-pointer w-10 relative py-2 px-2 my-4 text-sm text-white transition-all border h-full rounded-lg text-slate-400 border-white hover:text-slate-300`}
                                    >
                                        <div className="relative">
                                            <ArrowDownToLine />
                                            <Pen className='absolute -top-1 -right-1 w-3 h-3' />
                                        </div>
                                    </button>
                                    <p className='description2'>
                                        You can start create a distributed load, and to create a distributed load you need to click on the button and then click on the canvas to define first point of the distributed load and click on the canvas to define second point of the distributed load to define the line of the distributed load.
                                    </p>
                                    <p className='description2'>
                                        After you define where the distributed load will be applied, it will be shown on the canvas and you can define the magnitude and for each direction of the distributed load on sidebar.
                                        For the magnitude of the distributed load, we only support KiloNewton per meter per depth meter analysis (kN/m/m), and positive value (+) for x direction is directed to the right and positive value (+) for y direction is directed to the top of your model.
                                    </p>
                                </div>
                            </li>
                        </ul>
                    </div>

                    {/* Structural Components */}
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Input.subtitle[0].items[2]}</h3>
                        <p className="description2">
                            You can define the structural components that will be applied to the geometry that you have created.
                            TerraSim currently supports only one type of structural components, embedded beam row (EBR).
                        </p>
                        <ul className="pl-6 space-y-2 list-disc list-outside">
                            <li className='font-semibold'>Embedded Beam Row (EBR)
                                <div>
                                    <p className='description2'>User can create embedded beam row by using tools in the toolbar. The embedded beam row is defined as a structural component that would be applied to a EBR along it spacing direction (z direction of the canvas) for plane strain.</p>
                                    <button
                                        title="Draw Embedded Beam Row"
                                        className={`cursor-pointer w-10 relative py-2 px-2 my-4 text-sm text-white transition-all border h-full rounded-lg text-slate-400 border-white hover:text-slate-300`}
                                    >
                                        <div className="relative">
                                            <TestTube />
                                            <Pen className='absolute -top-1 -right-1 w-3 h-3' />
                                        </div>
                                    </button>
                                    <p className='description2'>
                                        You can start create a embedded beam row, and to create a embedded beam row you need to click on the button and then click on the canvas to define first point of the EBR and click on the canvas to define second point of the EBR to define the line of the EBR.
                                    </p>
                                    <p className='description2'>
                                        After you define where the EBR will be applied, it will be shown on the canvas and you can define the material properties of the EBR on sidebar.
                                    </p>
                                </div>
                            </li>
                        </ul>
                    </div>
                </div>
            </>
            {/* Water Table */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Input.subtitle[1].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Input.subtitle[1].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <p className="description2">
                            In this application water table can be defined as a polyline that define the boundary of the water table.
                            You can start draw the water table by click on the button and then click on the canvas to define the water table point (minimum 2 points), to finish your water table, you need to press enter on your keyboard.
                        </p>
                        <button
                            title="Draw Water Table"
                            className={`cursor-pointer w-10 h-10 relative py-2 px-2 my-4 text-sm text-white transition-all border rounded-lg text-slate-400 border-white hover:text-slate-300`}
                        >
                            <ChartNoAxesColumnIncreasing className='absolute bottom-2.5 left-1 w-5 h-5 -rotate-90' />
                            <ChartNoAxesColumnDecreasing className='absolute bottom-2.5 right-1 w-5 h-5 rotate-90' />
                            <Pen className='absolute top-1 right-1 w-3 h-3' />
                        </button>
                        <p className='description2'>
                            After you define where the water table will be applied, it will be shown on the canvas and on sidebar.
                            On the sidebar you can edit coordinates of the water table point, add new point, delete point, and delete the current water table.
                            You can also define multiple water table which you can activate or deactivate each of them on the staging tab to reflect condition of water table for each phase.
                        </p>
                    </div>
                </div>
            </>
            {/* Material */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Input.subtitle[2].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Input.subtitle[2].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Input.subtitle[2].items[0]}</h3>
                            <p className="description2">
                                We provide a simple and intuitive interface to draw polygons/rectangles and define the geometry of your soil model or structure as a cluster that you can use on the input tab.
                            </p>
                            <p className="description2">
                                We provide for multiple material properties that you can use on your soil model to represent different type of soil or material.
                                You can define the material properties on the sidebar by selecting the material properties from the dropdown menu. there are 2 type of material properties that you can use on your soil model, they are:
                            </p>
                            <ul className="pl-6 space-y-2 list-disc list-outside mb-4">
                                <li>
                                    <strong>Linear Elastic</strong>
                                </li>
                                <li>
                                    <strong>Mohr-Coulomb</strong>
                                </li>
                                <li>
                                    <strong>Hoek-Brown</strong>
                                </li>
                            </ul>
                            <p className='description2'>
                                For each material model you can define their parameters input on the panel that will be appear after you click edit button on the side of each material on the material list.
                                Every material model has a different stiffness and strength parameters input and also different drainage type that will be effected with water table in the analysis.
                                You can also define the color of the material that will be shown on the canvas if there is any geometry that is assigned to the material.
                            </p>
                        </div>
                        <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Input.subtitle[2].items[1]}</h3>
                            <p className="description2">
                                After you defined every material properties that you need, you can assign them to the geometry that you created before.
                                There are 2 way to assign material to the geometry, you can assign them by selecting the geometry on the canvas and then klik right on the mouse button, a context menu will appear and you can select 'assign material' and then select the material from the context menu, or you can assign them by selecting the material on the sidebar and then select the geometry on the canvas.
                                Each time you assign a material to a geometry, the geometry will be colored with the color of the material that you assigned to it.
                            </p>
                        </div>
                    </div>
                </div>
            </>
        </div>
    </PhaseWrapper>
);

const Phase2Content = () => (
    <PhaseWrapper
        title={Structure.Mesh.title}
        desc={Structure.Mesh.desc}
    >
        <div className="flex flex-col gap-4">
            <p className="description2">
                TerraSim uses a mesh to discretize the soil model into smaller elements that can be analyzed.
                The mesh is created by dividing the soil model into a grid of smaller elements.
                The smaller the elements, the more accurate the analysis and the longer it takes to complete the analysis.
                TerraSim uses a triangular mesh to discretize the geometry that will be generate 6 nodes for each element and 3 integration points for each element.
            </p>
            {/* Mesh Control Parameters */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Mesh.subtitle[0].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Mesh.subtitle[0].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Mesh.subtitle[0].items[0]}</h3>
                            <p className="description2">
                                You can adjust maximum size of the mesh that would be created on the canvas and analyze.
                                This value is represent the maximum length of th edge of the element (side length of triangle).
                            </p>
                        </div>
                        <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Mesh.subtitle[0].items[1]}</h3>
                            <p className="description2">
                                The refinement input value will represent how many multiple of the maximum size of the mesh that would be created near at the boundary of the geometry.
                                For example, if the maximum size is 1 and the refinement is 2, the mesh size will be 0.5.
                            </p>
                        </div>
                    </div>
                </div>
            </>
            {/* Mesh Control Parameters */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Mesh.subtitle[1].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Mesh.subtitle[1].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <div className="mb-4">
                            <p className="description2">
                                You can start generate the geometry by clicking the generate button on the top bar.
                                The geometry will be generated based on the parameters that you defined on the input tab.
                                Generate function will be executed in the server side and the result will be sent back to the user.
                                The result will be displayed on the canvas and the result tab.
                            </p>
                            <p className="description2">
                                Please be aware, if you define the mesh size too very small, the generate function will take a long time to complete, and it may not give you a good result.
                                Also, if you define the mesh size too large, the result will not be accurate.
                            </p>
                            <p className="description2">
                                You can check how many elements and nodes were generated after generate process is completed.
                                And for some reason, if you generate more than 4000 elements, the analysis will not be started.
                                This is because the server side is not optimized for large number of elements, consider to reduce the number of elements.
                            </p>
                        </div>
                    </div>
                </div>
            </>
        </div>
    </PhaseWrapper>
);

const Phase3Content = () => (
    <PhaseWrapper
        title={Structure.Staging.title}
        desc={Structure.Staging.desc}
    >
        <div className="flex flex-col gap-4">
            <p className="description2">
                The Staging Tab allows you to simulate the construction process by defining a sequence of calculation phases. Each phase represents a state of the soil model and structure at a specific point in time or construction stage.
            </p>
            {/* Phase Analysis Type */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Staging.subtitle[0].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Staging.subtitle[0].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Staging.subtitle[0].items[0]}</h3>
                            <p className="description2">
                                <strong>K0 Procedure:</strong> Used to generate initial stresses for horizontal ground surfaces with horizontal soil layers. It directly calculates vertical and horizontal stresses based on the weight of the soil and the Coefficient of Lateral Earth Pressure (K0).
                            </p>
                        </div>
                        {/* <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Staging.subtitle[0].items[1]}</h3>
                            <p className="description2">
                                <strong>Gravity Loading:</strong> Used for non-horizontal ground surfaces (slopes) to generate initial stresses. It applies the soil weight as a load and calculates the resulting stress state using plastic analysis.
                            </p>
                        </div> */}
                        <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Staging.subtitle[0].items[1]}</h3>
                            <p className="description2">
                                <strong>Plastic Analysis:</strong> Standard elastoplastic analysis for construction stages. Used for excavation, loading, embankment, etc. It solves for equilibrium under the applied changes.
                            </p>
                        </div>
                        <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Staging.subtitle[0].items[2]}</h3>
                            <p className="description2">
                                <strong>Safety Analysis (SRM):</strong> Uses the Strength Reduction Method to calculate the global Factor of Safety (FoS). It progressively reduces the strength parameters (c and phi for Mohr-Coulomb) of the soil until failure occurs.
                            </p>
                        </div>
                    </div>
                </div>
            </>
            {/* Schema of Phases & Component Activation */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Staging.subtitle[1].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Staging.subtitle[1].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Staging.subtitle[1].items[0]}</h3>
                            <p className="description2">
                                You can define the construction sequence by adding new phases. Each phase starts from the results of its parent phase.
                            </p>
                        </div>
                        <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Staging.subtitle[1].items[1]}</h3>
                            <p className="description2">
                                <strong>Component Explorer:</strong> In the Staging Tab, use the sidebar checkboxes to activate or deactivate components for the selected phase, or you can right click on the component in the canvas view to activate or deactivate it for the selected phase.
                            </p>
                            <ul className="pl-6 space-y-1 list-disc list-outside description2 mt-2">
                                <li><strong>Polygons:</strong> Uncheck to simulate excavation. Check to simulate backfilling or construction of embankments.</li>
                                <li><strong>Loads:</strong> Check to apply external loads (Point or Line loads) in this phase.</li>
                                <li><strong>Structures:</strong> Check to activate or deactivate structures in this phase.</li>
                            </ul>
                        </div>
                        <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Staging.subtitle[1].items[2]}</h3>
                            <p className="description2">
                                <strong>Active Water Level:</strong> Select the active Global Water Level for the phase from the 'Component Explorer' sidebar or by right clicking on the water level in the canvas view. Changing the water level simulates raising/lowering the water table or dewatering.
                            </p>
                        </div>
                        <div className="mb-4">
                            <h3 className="text-xl font-bold text-white leading-none mb-2">{Structure.Staging.subtitle[1].items[3]}</h3>
                            <p className="description2">
                                <strong>Change Material Properties:</strong> To simulate ground improvement or material changes (e.g., concrete hardening), you can override the material of a polygon for a specific phase.
                                <br />
                                <span className="italic text-slate-400 mt-1 block">Right-click on a polygon in the canvas while in the Staging Tab and select "Override Material".</span>
                            </p>
                        </div>
                    </div>
                </div>
            </>
        </div>
    </PhaseWrapper>
);

const Phase4Content = () => (
    <PhaseWrapper
        title={Structure.Results.title}
        desc={Structure.Results.desc}
    >
        <div className="flex flex-col gap-4">
            <p className="description2">
                The Results Tab is where you execute the finite element analysis and visualize the behavior of your model across all defined phases.
            </p>

            {/* Running Analysis */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Results.subtitle[0].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Results.subtitle[0].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <p className="description2">
                            To start the calculation, navigate to the Results Tab and click the <strong>Run Analysis</strong> button in the sidebar.
                            The application will stream the calculation data from the server, allowing you to monitor progress in real-time.
                        </p>
                        <div className="space-y-4 mt-2">
                            <div>
                                <h3 className="text-lg font-bold text-white leading-none mb-2">Detailed Components:</h3>
                                <ul className="pl-6 space-y-2 list-disc list-outside description2">
                                    <li><strong>{Structure.Results.subtitle[0].items[0]}:</strong> Use these buttons to control the backend solver process.</li>
                                    <li><strong>{Structure.Results.subtitle[0].items[1]}:</strong> During the calculation, a live chart displays the advancement of the analysis stage (Mstage or Sum-Msf) against the maximum displacement.</li>
                                    <li><strong>{Structure.Results.subtitle[0].items[2]}:</strong> The 'Analysis Log Progress' panel shows detailed solver output, including iteration counts and convergence errors.</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </>

            {/* Visualizing Results */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Results.subtitle[1].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Results.subtitle[1].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <p className="description2">
                            After the analysis (or during a live run), you can switch between several output views to inspect different physical quantities:
                        </p>
                        <div className="flex flex-col gap-6 mt-2">
                            <div className="space-y-3">
                                <h3 className="text-sm font-bold text-white uppercase tracking-widest">Deformation</h3>
                                <ul className="pl-6 space-y-1 list-disc list-outside description2">
                                    <li><strong>{Structure.Results.subtitle[1].items[0]}:</strong> Visualize the physical movement of the soil through mesh distortion or colored contour maps. You can adjust the <i>Deformation Scale</i> slider to exaggerate movements.</li>
                                </ul>
                            </div>
                            <div className="space-y-3">
                                <h3 className="text-sm font-bold text-white uppercase tracking-widest">Stresses & PWP</h3>
                                <ul className="pl-6 space-y-1 list-disc list-outside description2">
                                    <li><strong>{Structure.Results.subtitle[1].items[1]}:</strong> Visualize Total/Effective stresses and Pore Water Pressure variants.</li>
                                    <li><strong>{Structure.Results.subtitle[1].items[2]}:</strong> Highlights Gauss points that have reached the failure envelope.</li>
                                </ul>
                            </div>
                        </div>
                        <p className="description2 mt-4">
                            <span className="italic text-slate-400">Tip: Enable the <strong>Nodes</strong> or <strong>Gauss Points</strong> checkboxes in the control panel to hover over specific points and see exact numerical values.</span>
                        </p>
                    </div>
                </div>
            </>

            {/* Result Summary */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Results.subtitle[2].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Results.subtitle[2].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="pl-2 flex flex-col gap-2 mb-4">
                        <p className="description2">
                            The sidebar provides a quantitative summary for the currently selected phase, including:
                        </p>
                        <ul className="pl-6 space-y-2 list-disc list-outside description2">
                            <li><strong>{Structure.Results.subtitle[2].items[0]}:</strong> Minimum and maximum values for Displacements, Stresses, and PWP.</li>
                            <li><strong>{Structure.Results.subtitle[2].items[1]}:</strong> A count of how many integration points have turned plastic.</li>
                            <li><strong>{Structure.Results.subtitle[2].items[2]}:</strong> Identification of the exactly which step failed and what level was reached.</li>
                        </ul>
                    </div>
                </div>
            </>
        </div>
    </PhaseWrapper>
);

const Phase5Content: React.FC = () => (
    <PhaseWrapper
        title={Structure.Project.title}
        desc={Structure.Project.desc}
    >
        <div className="flex flex-col gap-4">
            <p className="description2">
                Project management tools are located in the top bar, allowing you to save, load, and configure your simulation environment.
            </p>

            {/* Header Controls */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Project.subtitle[0].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Project.subtitle[0].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="flex flex-col gap-8 pl-2">
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[0].items[0]}</h3>
                            <p className="description2">
                                You can change your project name directly in the header by clicking on the text next to the logo. This name is used when saving files.
                            </p>
                        </div>

                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[0].items[1]}</h3>
                            <p className="description2">
                                Use the messaging icon to report bugs or suggest features.
                            </p>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[0].items[2]}</h3>
                            <p className="description2">
                                You can load sample projects from the TerraSim library.
                            </p>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[0].items[3]}</h3>
                            <p className="description2">
                                The bell icon notifies you of new versions and features added to TerraSim.
                            </p>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[0].items[4]}</h3>
                            <p className="description2">
                                Open the Documentation tab to learn more about TerraSim features and capabilities.
                            </p>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[0].items[5]}</h3>
                            <p className="description2">
                                Open App Settings panel where you can adjust your simulation environment.
                            </p>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[0].items[6]}</h3>
                            <p className="description2">
                                Switch between light and dark modes to reduce eye strain.
                            </p>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[0].items[7]}</h3>
                            <p className="description2">
                                Open the user panel to manage your file projects.
                            </p>
                        </div>
                    </div>
                </div>
            </>

            {/* User Panel */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Project.subtitle[1].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Project.subtitle[1].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="flex flex-col gap-8 pl-2">
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[1].items[0]}</h3>
                            <p className="description2">
                                You can reset your project to its initial state and clear all results including geometry and material properties.
                            </p>
                        </div>

                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[1].items[1]}</h3>
                            <p className="description2">
                                You can download your project as a .tsm file to save it locally.
                            </p>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[1].items[2]}</h3>
                            <p className="description2">
                                You can save your projects on the cloud to access them from any device.
                            </p>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[1].items[3]}</h3>
                            <p className="description2">
                                Same as Save project on cloud, but it will save as a new project.
                            </p>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[1].items[4]}</h3>
                            <p className="description2">
                                You can load your projects from the cloud to access them from any device.
                            </p>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[1].items[5]}</h3>
                            <p className="description2">
                                You can load your .tsm file project that you saved/downloaded locally.
                            </p>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-white mb-2">{Structure.Project.subtitle[1].items[6]}</h3>
                            <p className="description2">
                                You can logout from your account.
                            </p>
                        </div>
                    </div>
                </div>
            </>

            {/* Application Settings */}
            <>
                <div className="flex-1 ml-4 mb-4 space-y-4 py-2 border-b border-gray-500">
                    <h2 className="text-2xl font-black text-white">{Structure.Project.subtitle[2].title}</h2>
                    <p className="text-lg text-slate-400 leading-relaxed max-w-3xl">
                        {Structure.Project.subtitle[2].desc}
                    </p>
                </div>
                <div className="flex flex-col ml-8 gap-4">
                    <div className="pl-2 space-y-8">
                        <div>
                            <h3 className="text-xl font-bold text-white mb-4">{Structure.Project.subtitle[2].items[0]}</h3>
                            <div className="flex flex-col gap-4">
                                <div className="">
                                    <h4 className="font-bold text-white mb-1">Hide Grid</h4>
                                    <p className="text-xs text-slate-400">Hides the grid lines for a cleaner view.</p>
                                </div>
                                <div className="">
                                    <h4 className="font-bold text-white mb-1">Hide Rulers</h4>
                                    <p className="text-xs text-slate-400">Hides the rulers that show the dimensions of the canvas.</p>
                                </div>
                                <div className="">
                                    <h4 className="font-bold text-white mb-1">Snap to Grid</h4>
                                    <p className="text-xs text-slate-400">Forces drawing tools to align with the grid intersections, ensuring precise geometry.</p>
                                </div>
                                <div className="">
                                    <h4 className="font-bold text-white mb-1">Grid Spacing</h4>
                                    <p className="text-xs text-slate-400">Sets the distance between grid lines in meters (default is 1.0m).</p>
                                </div>
                            </div>
                        </div>

                        <div>
                            <h3 className="text-xl font-bold text-white mb-4">{Structure.Project.subtitle[2].items[1]}</h3>
                            <div className="flex flex-col gap-4">
                                <div className="">
                                    <h4 className="font-bold text-white mb-1 text-sm">Tolerance (&epsilon;)</h4>
                                    <p className="text-[11px] text-slate-400">The convergence criterion for iterations. Smaller values increase accuracy but may slow down the solver.</p>
                                </div>
                                <div className="">
                                    <h4 className="font-bold text-white mb-1 text-sm">Max Iterations</h4>
                                    <p className="text-[11px] text-slate-400">The maximum number of attempts the solver will make to converge within a single step.</p>
                                </div>
                                <div className="">
                                    <h4 className="font-bold text-white mb-1 text-sm">Initial Step Size</h4>
                                    <p className="text-[11px] text-slate-400">The load increment fraction applied at the beginning of a plastic analysis phase.</p>
                                </div>
                                <div className="">
                                    <h4 className="font-bold text-white mb-1 text-sm">Desired Iterations</h4>
                                    <p className="text-[11px] text-slate-400">The solver adjusts future step sizes to try and reach convergence within this iteration range (e.g., 3-7 iterations).</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </>
        </div>
    </PhaseWrapper>
);

export const UserManual: React.FC = () => {
    return (
        <div className="space-y-16 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <header className="space-y-4">
                <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight leading-tight">
                    User Manual
                </h1>
                <p className="text-xl text-slate-400 leading-relaxed max-w-2xl">
                    Follow this step-by-step guide to navigate the TerraSim workflow and master geotechnical simulation.
                </p>
            </header>

            <div className="space-y-24 relative lg:before:absolute lg:before:left-8 lg:before:top-24 lg:before:bottom-0 lg:before:w-px lg:before:bg-transparent">
                <Phase1Content />
                <Phase2Content />
                <Phase3Content />
                <Phase4Content />
                <Phase5Content />
            </div>

            {/* <div className="bg-amber-500/10 border border-amber-500/20 rounded-3xl p-8 flex flex-col md:flex-row gap-6 items-start">
                <div className="p-3 bg-amber-500 rounded-2xl text-slate-950 shrink-0 shadow-lg shadow-amber-500/20">
                    <Info className="w-8 h-8" />
                </div>
                <div className="space-y-3">
                    <h3 className="text-xl font-bold text-white leading-none">Tip: Local & Cloud Saving</h3>
                    <p className="text-slate-400 leading-relaxed">
                        Always use the 'Local Save' (.tsm file) to keep a personal backup of your work. The 'Cloud Save' feature is perfect for syncing between devices and collaborating, but offline backups ensure your data is always safe regardless of internet connectivity.
                    </p>
                </div>
            </div> */}
        </div>
    );
};
