import { PhaseRequest, PolygonData } from "../types";

export const propagateMaterialChanges = (
    allPhases: PhaseRequest[],
    changedPhaseId: string,
    oldCurrentMat: Record<number, string>,
    polygons: PolygonData[]
) => {
    const changedPhase = allPhases.find(p => p.id === changedPhaseId);
    if (!changedPhase) return;

    const newCurrentMat = changedPhase.current_material;

    // Find children
    allPhases.filter(p => p.parent_id === changedPhaseId).forEach(child => {
        // const oldChildParentMat = { ...child.parent_material }; // Unused but kept for reference logic
        const oldChildCurrentMat = { ...child.current_material };

        // 1. Update Child's parent_material -> Snapshot of Parent's new current
        child.parent_material = { ...newCurrentMat };

        // 2. Update Child's current_material based on inheritance
        const newChildCurrentMat: Record<number, string> = {};

        const childActiveSet = new Set(child.active_polygon_indices);

        childActiveSet.forEach(polyIdx => {
            // If it was in old child current
            if (polyIdx in oldChildCurrentMat) {
                const childVal = oldChildCurrentMat[polyIdx];
                const parentValOld = oldCurrentMat[polyIdx];
                const parentValNew = newCurrentMat[polyIdx];

                if (childVal === parentValOld && parentValNew) {
                    // Inherited -> Update
                    newChildCurrentMat[polyIdx] = parentValNew;
                } else {
                    // User override or no parent change -> Keep
                    newChildCurrentMat[polyIdx] = childVal;
                }
            } else {
                // Newly active in child? Or missing? 
                if (newCurrentMat[polyIdx]) {
                    newChildCurrentMat[polyIdx] = newCurrentMat[polyIdx];
                } else if (polygons[polyIdx]) {
                    newChildCurrentMat[polyIdx] = polygons[polyIdx].materialId;
                }
            }
        });

        child.current_material = newChildCurrentMat;

        // Recurse
        propagateMaterialChanges(allPhases, child.id, oldChildCurrentMat, polygons);
    });
}
