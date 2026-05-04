export interface Pose {
  pose_id: string;
  name: string;
  sanskrit_name?: string;
  expertise_level?: string;
  pose_categories: string[];
  image_url?: string;
  description?: string;
  tags: string[];
}

export interface FlowBlock {
  id: string;
  order: number;
  block_type: 'pose' | 'transition' | 'talking_point' | 'custom';
  pose_id?: string;
  pose_name?: string;
  talking_point_id?: string;
  description?: string;
  duration: number;
  side?: 'left' | 'right' | 'both';
  pair_id?: string;
  notes?: string;
}

export interface FlowSection {
  id: string;
  label: string;
  blocks: FlowBlock[];
}

export interface Flow {
  flow_id: string;
  flow_name: string;
  description?: string;
  context_type: string;
  tags: string[];
  created_at: string;
  updated_at?: string;
  versions: FlowVersion[];
}

export interface FlowVersion {
  version_id: string;
  flow_id: string;
  version_number: number;
  blocks_json: string;
  vibe_profile?: string;
  duration_minutes?: number;
  created_at: string;
}

export interface ClassSession {
  session_id: string;
  flow_version_id?: string;
  session_date: string;
  start_time?: string;
  end_time?: string;
  location?: string;
  context_type: string;
  spotify_playlist_id?: string;
  notes?: string;
  flow_name?: string;
  assessment?: Assessment;
}

export interface Assessment {
  assessment_id: string;
  session_id: string;
  vibe_score?: number;
  flow_score?: number;
  playlist_score?: number;
  comment_text?: string;
  tags?: string[];
}

export interface Theme {
  theme_id: string;
  name: string;
  description?: string;
  tags: string[];
}

export interface TalkingPoint {
  talking_point_id: string;
  theme_id?: string;
  type: string;
  content: string;
  tags: string[];
}

export interface ConfigStatus {
  configured: boolean;
  fast_model?: string;
  power_model?: string;
  spotify_connected: boolean;
  data_loaded: {
    poses: boolean;
    themes: boolean;
    tracks: boolean;
  };
}
