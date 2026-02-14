
import { SAMPLE_FOUNDATION } from './sample_Foundation';
import { SAMPLE_RETAINING_WALL } from './sample_RetainingWall';

export interface SampleManifest {
    id: string;
    name: string;
    description: string;
    data: any; // Using any for flexibility, but ideally should match partial ProjectFile or specific structure
}

export const AVAILABLE_SAMPLES: SampleManifest[] = [
    {
        id: 'foundation',
        name: 'Foundation Construction',
        description: 'Simple foundation construction on soft soil with plastic and safety analysis.',
        data: SAMPLE_FOUNDATION
    },
    {
        id: 'retaining_wall',
        name: 'Retaining Wall Embankment',
        description: 'Simple embankment with retaining wall, multiple fill stages, and line loads.',
        data: SAMPLE_RETAINING_WALL
    }
];
