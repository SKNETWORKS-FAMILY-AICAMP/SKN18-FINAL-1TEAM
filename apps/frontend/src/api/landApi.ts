import { Land, LandFilterParams } from '../types/land';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchLands(params?: LandFilterParams): Promise<Land[]> {
    const queryParams = new URLSearchParams();

    if (params) {
        // 자치구 + 행정동을 조합하여 address로 전달
        let addressFilter = '';
        if (params.region) addressFilter = params.region;
        if (params.dong) addressFilter += (addressFilter ? ' ' : '') + params.dong;

        if (addressFilter) queryParams.append('address', addressFilter);
        if (params.transaction_type) queryParams.append('deal_type', params.transaction_type);
        if (params.building_type) queryParams.append('building_type', params.building_type);
        if (params.search) queryParams.append('search', params.search);
    }

    const response = await fetch(`${API_BASE_URL}/api/listings/lands/?${queryParams.toString()}`);

    if (!response.ok) {
        throw new Error('Failed to fetch lands');
    }

    const data = await response.json();
    return data.results || data; // DRF pagination support
}

export async function fetchLandById(id: string): Promise<Land> {
    const response = await fetch(`${API_BASE_URL}/api/listings/lands/${id}/`);

    if (!response.ok) {
        throw new Error('Failed to fetch land details');
    }

    return response.json();
}

export async function fetchSimilarListings(landId: string): Promise<Land[]> {
    const response = await fetch(`${API_BASE_URL}/api/listings/lands/${landId}/similar_listings/`);

    if (!response.ok) {
        throw new Error('Failed to fetch similar listings');
    }

    const data = await response.json();
    return data.results || [];
}

export interface LandLocation {
    id: string;
    latitude: number;
    longitude: number;
    address: string;
    name: string;
    price?: string;
    deal_type?: string;
    building_type?: string;
    area?: string;
}

export async function fetchLandLocations(params?: {
    limit?: number;
    land_id?: string;
    address?: string;
    deal_type?: string;
}): Promise<LandLocation[]> {
    const queryParams = new URLSearchParams();

    if (params) {
        if (params.limit) queryParams.append('limit', params.limit.toString());
        if (params.land_id) queryParams.append('land_id', params.land_id);
        if (params.address) queryParams.append('address', params.address);
        if (params.deal_type) queryParams.append('deal_type', params.deal_type);
    }

    const response = await fetch(`${API_BASE_URL}/api/listings/lands/locations/?${queryParams.toString()}`);

    if (!response.ok) {
        throw new Error('Failed to fetch land locations');
    }

    const data = await response.json();
    return data.results || [];
}

export interface FacilityInfo {
    count: number;
    name: string;
    icon: string;
}

export interface NearbyFacilities {
    medical: FacilityInfo;
    convenience: FacilityInfo;
    transportation: FacilityInfo;
    safety: FacilityInfo;
    location?: {
        latitude: number;
        longitude: number;
    };
}

export async function fetchNearbyFacilities(landId: string): Promise<NearbyFacilities> {
    const response = await fetch(`${API_BASE_URL}/api/listings/lands/${landId}/nearby_facilities/`);

    if (!response.ok) {
        throw new Error('Failed to fetch nearby facilities');
    }

    return response.json();
}

export interface FacilityLocation {
    name: string;
    latitude: number;
    longitude: number;
    type: string;
    category: string;
}

export interface FacilityLocationsResponse {
    category: string;
    count: number;
    facilities: FacilityLocation[];
}

export async function fetchFacilityLocations(
    landId: string,
    category: 'transportation' | 'medical' | 'convenience' | 'safety'
): Promise<FacilityLocationsResponse> {
    const response = await fetch(
        `${API_BASE_URL}/api/listings/lands/${landId}/facility_locations/?category=${category}`
    );

    if (!response.ok) {
        throw new Error('Failed to fetch facility locations');
    }

    return response.json();
}

