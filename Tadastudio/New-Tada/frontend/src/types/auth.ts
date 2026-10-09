// frontend/src/types/auth.ts

/**
 * Authentication types for OAuth2 proxy-based authentication.
 * All authentication is handled by OAuth2 proxy upstream.
 */

export interface AuthUser {
	email?: string; // Primary email identifier
	name?: string; // Full display name
	first_name?: string; // User's first name
	last_name?: string; // User's last name

	// OAuth2/OIDC claims from identity provider
	sub?: string; // Subject identifier
	preferred_username?: string; // Preferred username
	given_name?: string; // Given name from claims
	family_name?: string; // Family name from claims
	tid?: string; // Tenant ID (Microsoft/Azure AD)
	oid?: string; // Object ID (Microsoft/Azure AD)

	// Auth metadata
	auth_source?: string; // Authentication source (e.g. "oauth_proxy", "skip_auth")

	// RBAC fields
	is_admin?: boolean; // Whether user has admin privileges
	groups?: string[]; // OAuth group membership for RBAC
	role?: "PENDING" | "USER" | "ADMIN"; // User role from database
	is_pending?: boolean; // Whether user account is pending approval
}

export interface AuthContextType {
	isAuthenticated: boolean;
	user: AuthUser | null;
	apiReady: boolean;
	loading: boolean;
	logout: () => Promise<void>;
}
