// TypeScript types matching backend schemas

// ============= Enums =============

export type UserType = 'user' | 'consultant';

export type Gender = 'male' | 'female';

export type ActivityLevel = 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active';

export type GoalType = 'lose' | 'gain' | 'maintain';

export type ApplicationStatus = 'submitted' | 'rejected' | 'cancelled' | 'proposed' | 'proposal_accepted' | 'scheduled';
export type ConsultantType = 'clinical' | 'non_clinical' | 'wellness';
export type DocumentType = 'degree' | 'certificate' | 'license' | 'internship' | 'experience';

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

export interface PatientSummaryRead {
    patient: {
        id: string;
        username: string;
        email: string;
        full_name: string | null;
    };
    user_data: UserDataRead | null;
    goal: GoalRead | null;
    nutrition_target: NutritionTargetRead | null;
    logs: GoalLogRead[];
}

export interface UserRead {
    id: string;
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
    id: string;
    created_for: string | null;
    created_by: string | null;
    goal_type: GoalType;
    target_weight: number | null;
    initial_weight: number | null;
    duration_days: number | null;
    start_date: string | null;
    end_date: string | null;
    active: boolean;
    created_at: string;
    updated_at: string;
}

export interface GoalUpsert {
    goal_type: GoalType;
    target_weight?: number | null;
    duration_days?: number | null;
    start_date?: string | null;
    end_date?: string | null;
}

export interface GoalLogRead {
    id: string;
    user_id: string;
    goal_id: string;
    date: string;
    weight: number;
    due_terget: number;
}

export interface GoalLogCreate {
    weight: number;
    date?: string;
}

// ============= Nutrition Target =============

export interface NutritionTargetRead {
    id: number;
    user_id: number;
    calories_kcal: number;
    protein_g: number;
    carbs_g: number;
    fat_g: number;
    active: boolean;
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
    user_id: string;  // primary key (used as the consultant's public ID)
    display_name: string;
    bio: string | null;
    specialties: string | null;
    other_info: string | null;
    consultant_type: ConsultantType;
    highest_qualification: string;
    graduation_institution: string | null;
    is_verified: boolean;
}

export interface ConsultantProfileRead {
    user_id: string;  // primary key
    display_name: string;
    bio: string | null;
    specialties: string | null;
    other_info: string | null;
    consultant_type: ConsultantType;
    highest_qualification: string;
    graduation_institution: string | null;
    registration_body: string | null;
    registration_number: string | null;
    is_verified: boolean;
    created_at: string;
    updated_at: string;
}

export interface ConsultantProfileCreate {
    display_name: string;
    bio?: string | null;
    specialties?: string | null;
    other_info?: string | null;
    consultant_type: ConsultantType;
    highest_qualification: string;
    graduation_institution?: string | null;
    registration_body?: string | null;
    registration_number?: string | null;
}

export interface ConsultantProfileUpdate {
    display_name?: string | null;
    bio?: string | null;
    specialties?: string | null;
    other_info?: string | null;
    consultant_type?: ConsultantType | null;
    highest_qualification?: string | null;
    graduation_institution?: string | null;
    registration_body?: string | null;
    registration_number?: string | null;
}

export interface ConsultantDocumentRead {
    id: string;
    consultant_profile_id: string;
    doc_type: DocumentType;
    issuer: string | null;
    issue_date: string | null;
    expires_at: string | null;
    bucket: string;
    file_path: string;
    is_verified: boolean;
    verification_note: string | null;
    created_at: string;
}

// ============= Availability Rules =============

export interface AvailabilityRuleCreate {
    day_of_week: number;
    start_time: string;
    end_time: string;
    timezone?: string;
    consultation_duration: number;
}

export interface AvailabilityRuleRead {
    id: string;
    consultant_profile_id: string;
    day_of_week: number;
    start_time: string;
    end_time: string;
    timezone: string;
    consultation_duration: number;
    is_active: boolean;
}

export interface AvailabilityRuleUpdate {
    start_time?: string;
    end_time?: string;
    consultation_duration?: number;
    is_active?: boolean;
}

// ============= Appointments =============

export interface AppointmentApplicationCreate {
    consultant_user_id: number;
    requested_start_at: string;
    note_from_user?: string | null;
}

export interface AppointmentApplicationRead {
    id: number;
    user_id: number;
    consultant_user_id: number;
    note_from_user: string | null;
    requested_start_at: string;
    proposed_start_at: string | null;
    proposed_at: string | null;
    proposal_accepted_at: string | null;
    status: ApplicationStatus;
    created_at: string;
    updated_at: string;
}

export interface AppointmentSchedule {
    scheduled_start_at: string;
    scheduled_end_at: string;
}

export interface ProposeTimeRequest {
    proposed_start_at: string;
}

export interface FreeWindowResponse {
    start: string;
    end: string;
}

export interface AppointmentRead {
    id: string;
    application_id: string | null;
    user_id: string;
    consultant_user_id: string;
    scheduled_start_at: string;
    scheduled_end_at: string;
    status: AppointmentStatus;
    consultant_access: boolean;
    followup_room_id: string | null;
    created_at: string;
    updated_at: string;
    // Populated from joins
    consultant?: ConsultantPublicRead;
    // Participant info from AppointmentWithParticipants
    user_name?: string | null;
    user_email?: string | null;
    consultant_name?: string | null;
    consultant_email?: string | null;
    session_status?: 'not_started' | 'active' | 'ended' | null;
}

export interface AppointmentReadWithUser extends AppointmentRead {
    user: UserRead;
    user_data?: UserDataRead;
    session_status?: 'not_started' | 'active' | 'ended';
}

export interface AppointmentDetailsResponse {
    appointment: AppointmentRead;
    goal?: GoalRead | null;
    nutrition_target?: NutritionTargetRead | null;
    consultant?: UserRead | null;
}

// ============= Sessions =============

export type SessionRoomRead = {
    id: string;
    appointment_id: string;
    status: "not_started" | "active" | "ended";
    started_at: string | null;
    ended_at: string | null;
    started_by_user_id: string | null;
    ended_by_user_id: string | null;
    created_at: string;
    updated_at: string;
};


export interface ChatMessageCreate {
    message: string;
}

export interface ChatMessageRead {
    id: string;
    room_id: string;
    sender_user_id: string;
    message: string;
    sent_at: string;
}

export interface SessionNoteCreate {
    note: string;
    is_visible_to_user?: boolean;
}

export interface SessionNoteRead {
    id: string;
    appointment_id: string;
    created_by_user_id: string;
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

// ============= Follow-ups =============

export type FollowUpRoomStatus = 'active' | 'closed';
export type ProposalStatus = 'pending' | 'accepted' | 'rejected' | 'cancelled';

export interface FollowUpRoomRead {
    id: string;
    user_id: string;
    consultant_user_id: string;
    created_from_appointment_id?: string | null;
    status: FollowUpRoomStatus;
    last_message_at: string;
    cancelled_by_user_id?: string | null;
    cancelled_at?: string | null;
    reactivated_at?: string | null;
    created_at: string;
    updated_at: string;
    // enrichment fields
    other_party_name?: string | null;
    other_party_email?: string | null;
    cancelled_by_name?: string | null;
}

export interface FollowUpMessage {
    id: string;
    room_id: string;
    sender_user_id: string;
    message: string;
    is_system: boolean;
    sent_at: string;
}

export interface TimeProposal {
    id: string;
    room_id: string;
    proposed_by_user_id: string;
    start_at: string;
    end_at: string;
    status: ProposalStatus;
    responded_by_user_id: string | null;
    responded_at: string | null;
    appointment_id: string | null;
    created_at: string;
    updated_at: string;
}

export interface CreateRoomRequest {
    other_user_id: string;
}

export interface SendMessageRequest {
    message: string;
}

export interface CreateProposalRequest {
    start_at: string;
    end_at: string;
}
