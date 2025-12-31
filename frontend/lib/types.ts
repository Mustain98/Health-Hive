// TypeScript types matching backend schemas

// ============= Enums =============

export type UserType = 'user' | 'consultant';

export type Gender = 'male' | 'female';

export type ActivityLevel = 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active';

export type GoalType = 'lose' | 'gain' | 'maintain';

export type ApplicationStatus = 'submitted' | 'rejected' | 'accepted' | 'cancelled';

export type AppointmentStatus = 'scheduled' | 'completed' | 'cancelled' | 'no_show';

export type RoomStatus = 'open' | 'closed';

export type PermissionScope = 'read' | 'read_write';

export type PermissionStatus = 'active' | 'revoked';

// ============= Auth & User =============

export interface UserLogin {
    identifier: string;
    password: string;
}

export interface UserRegister {
    username?: string;
    email: string;
    password: string;
    full_name?: string;
}

export interface UserRead {
    id: number;
    username: string;
    email: string;
    full_name: string | null;
    user_type: UserType;
}

export interface UserUpdate {
    username?: string;
    email?: string;
    full_name?: string;
    password?: string;
}

export interface Token {
    access_token: string;
    token_type: string;
}

// ============= User Data =============

export interface UserDataRead {
    id: number;
    user_id: number;
    age: number | null;
    gender: Gender | null;
    height_cm: number | null;
    weight_kg: number | null;
    activity_level: ActivityLevel | null;
    created_at: string;
    updated_at: string;
}

export interface UserDataUpdate {
    age?: number | null;
    gender?: Gender | null;
    height_cm?: number | null;
    weight_kg?: number | null;
    activity_level?: ActivityLevel | null;
}

// ============= Goal =============

export interface GoalRead {
    id: number;
    user_id: number;
    goal_type: GoalType;
    target_delta_kg: number | null;
    duration_days: number | null;
    start_date: string | null;
    end_date: string | null;
    created_at: string;
    updated_at: string;
}

export interface GoalUpsert {
    goal_type: GoalType;
    target_delta_kg?: number | null;
    duration_days?: number | null;
    start_date?: string | null;
    end_date?: string | null;
}

// ============= Nutrition Target =============

export interface NutritionTargetRead {
    id: number;
    user_id: number;
    calories_kcal: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
    created_at: string;
    updated_at: string;
}

export interface NutritionTargetUpdate {
    calories_kcal?: number | null;
    protein_g?: number | null;
    carbs_g?: number | null;
    fat_g?: number | null;
}

// ============= Consultant =============

export interface ConsultantPublicRead {
    id: number;
    user_id: number;
    display_name: string;
    bio: string | null;
    specialties: string | null;
    is_verified: boolean;
}

export interface ConsultantProfileRead {
    id: number;
    user_id: number;
    display_name: string;
    bio: string | null;
    specialties: string | null;
    other_info: string | null;
    is_verified: boolean;
    created_at: string;
    updated_at: string;
}

export interface ConsultantProfileCreate {
    display_name: string;
    bio?: string | null;
    specialties?: string | null;
    other_info?: string | null;
}

export interface ConsultantProfileUpdate {
    display_name?: string | null;
    bio?: string | null;
    specialties?: string | null;
    other_info?: string | null;
}

export interface ConsultantDocumentRead {
    id: number;
    consultant_profile_id: number;
    doc_type: string;
    title: string;
    issuer: string | null;
    issue_date: string | null;
    expires_at: string | null;
    mime_type: string;
    file_url: string | null;
    file_path: string | null;
    file_size_bytes: number | null;
    created_at: string;
}

// ============= Appointments =============

export interface AppointmentApplicationCreate {
    consultant_user_id: number;
    note_from_user?: string | null;
}

export interface AppointmentApplicationRead {
    id: number;
    user_id: number;
    consultant_user_id: number;
    note_from_user: string | null;
    status: ApplicationStatus;
    created_at: string;
    updated_at: string;
}

export interface AppointmentSchedule {
    scheduled_start_at: string;
    scheduled_end_at: string;
}

export interface AppointmentRead {
    id: number;
    application_id: number | null;
    user_id: number;
    consultant_user_id: number;
    scheduled_start_at: string;
    scheduled_end_at: string;
    status: AppointmentStatus;
    created_at: string;
    updated_at: string;
}

// ============= Sessions =============

export interface SessionRoomRead {
    id: number;
    appointment_id: number;
    status: RoomStatus;
    created_at: string;
    updated_at: string;
}

export interface ChatMessageCreate {
    message: string;
}

export interface ChatMessageRead {
    id: number;
    room_id: number;
    sender_user_id: number;
    message: string;
    sent_at: string;
}

export interface SessionNoteCreate {
    note: string;
    is_visible_to_user?: boolean;
}

export interface SessionNoteRead {
    id: number;
    appointment_id: number;
    created_by_user_id: number;
    note: string;
    is_visible_to_user: boolean;
    created_at: string;
    updated_at: string;
}

// ============= Permissions =============

export interface PermissionGrant {
    consultant_user_id: number;
    scope?: PermissionScope;
    resources: string[];
    granted_in_appointment_id?: number | null;
}

export interface PermissionRevoke {
    consultant_user_id: number;
}

export interface PermissionRead {
    id: number;
    user_id: number;
    consultant_user_id: number;
    scope: PermissionScope;
    resources: string[];
    status: PermissionStatus;
    granted_at: string;
    revoked_at: string | null;
    granted_in_appointment_id: number | null;
    created_at: string;
}
