export const DEMO_COORDS = { lat: 19.076, lng: 72.8754 };

export function isDemoMode() {
  if (typeof window === 'undefined') {
    return false;
  }
  const params = new URLSearchParams(window.location.search);
  return params.get('demo') === 'true';
}

export function getDemoNearbyResults() {
  const nowIso = new Date().toISOString();
  return [
    {
      id: 91001,
      name: 'KEM Hospital Emergency Wing',
      place_type: 'hospital',
      latitude: 19.0008,
      longitude: 72.8411,
      phone: '02224136051',
      address: 'Acharya Donde Marg, Parel, Mumbai',
      is_verified: true,
      geohash5: 'te7u4',
      source: 'demo_seed',
      data_confidence: 1.0,
      last_synced: nowIso,
      created_at: nowIso,
      distance_km: 2.1,
    },
    {
      id: 91002,
      name: 'Sion Hospital Casualty',
      place_type: 'hospital',
      latitude: 19.0469,
      longitude: 72.8634,
      phone: '02224076381',
      address: 'Dr Babasaheb Ambedkar Rd, Sion, Mumbai',
      is_verified: true,
      geohash5: 'te7u6',
      source: 'demo_seed',
      data_confidence: 1.0,
      last_synced: nowIso,
      created_at: nowIso,
      distance_km: 3.5,
    },
    {
      id: 91003,
      name: 'Dadar Police Station',
      place_type: 'police',
      latitude: 19.0207,
      longitude: 72.8434,
      phone: '02224146544',
      address: 'Senapati Bapat Marg, Dadar West, Mumbai',
      is_verified: true,
      geohash5: 'te7u5',
      source: 'demo_seed',
      data_confidence: 1.0,
      last_synced: nowIso,
      created_at: nowIso,
      distance_km: 1.7,
    },
    {
      id: 91004,
      name: '108 Ambulance Dispatch - Central Zone',
      place_type: 'ambulance',
      latitude: 19.0312,
      longitude: 72.8592,
      phone: '108',
      address: 'Central Dispatch Hub, Mumbai',
      is_verified: true,
      geohash5: 'te7u5',
      source: 'demo_seed',
      data_confidence: 1.0,
      last_synced: nowIso,
      created_at: nowIso,
      distance_km: 1.2,
    },
    {
      id: 91005,
      name: 'Mumbai Express Recovery Towing',
      place_type: 'towing',
      latitude: 19.0474,
      longitude: 72.8576,
      phone: '02224937777',
      address: 'Prabhadevi Service Lane, Mumbai',
      is_verified: true,
      geohash5: 'te7u6',
      source: 'demo_seed',
      data_confidence: 1.0,
      last_synced: nowIso,
      created_at: nowIso,
      distance_km: 2.9,
    },
  ];
}

export function getDemoSosResponse(lat, lng) {
  const maps = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
  return {
    sos_id: Number(`${Date.now()}`.slice(-6)),
    nearest_hospital: getDemoNearbyResults()[0],
    google_maps_link: maps,
    whatsapp_link: `https://wa.me/?text=${encodeURIComponent(`Demo SOS dispatched at ${lat},${lng}`)}`,
    sms_sent: true,
    demo_mode: true,
  };
}
