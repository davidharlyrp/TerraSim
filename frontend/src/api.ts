import { MeshRequest, MeshResponse, SolverRequest } from './types';
import { pb } from './pb';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8010/api';

export class ApiError extends Error {
    constructor(
        public status: number,
        public code: string,
        public title: string,
        public description: string
    ) {
        super(description);
        this.name = 'ApiError';
    }
}

async function handleResponse(response: Response) {
    if (!response.ok) {
        let errorData;
        try {
            errorData = await response.json();
        } catch (e) {
            throw new Error(`Request failed with status ${response.status}: ${response.statusText}`);
        }

        if (errorData && errorData.detail && typeof errorData.detail === 'object') {
            const { code, title, description } = errorData.detail;
            throw new ApiError(response.status, code, title, description);
        } else if (errorData && typeof errorData.detail === 'string') {
            throw new Error(errorData.detail);
        } else {
            throw new Error(`Request failed: ${response.statusText}`);
        }
    }
    return response.json();
}

export const api = {
    generateMesh: async (request: MeshRequest): Promise<MeshResponse> => {
        const token = pb.authStore.token;
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE_URL}/mesh/generate`, {
            method: 'POST',
            headers,
            body: JSON.stringify(request),
        });

        return handleResponse(response);
    },

    solve: async (request: SolverRequest, signal?: AbortSignal): Promise<Response> => {
        const token = pb.authStore.token;
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        return fetch(`${API_BASE_URL}/solver/calculate`, {
            method: 'POST',
            headers,
            body: JSON.stringify(request),
            signal
        });
    },
};
