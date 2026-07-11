// Shared types actually consumed by the admin app.
// (Everything else lives as local interfaces in app/admin/page.tsx.)

export type UserType = 'user' | 'consultant' | 'admin';

export interface UserRead {
    id: string;
    username: string;
    email: string;
    full_name: string | null;
    user_type: UserType;
}
