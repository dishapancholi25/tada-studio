"use client";

import type React from "react";
import {
	createContext,
	type ReactNode,
	useContext,
	useEffect,
	useState,
} from "react";
import { adminAPI } from "@/lib/admin-api";
import { useAuth } from "./AuthContext";

interface FeatureAccessContextType {
	featureAccess: Map<string, boolean>;
	loading: boolean;
	error: string | null;
	canAccessFeature: (featureName: string) => boolean;
	isFeatureAdminOnly: (featureName: string) => boolean;
	refreshFeatureAccess: () => Promise<void>;
}

const FeatureAccessContext = createContext<
	FeatureAccessContextType | undefined
>(undefined);

export const FeatureAccessProvider: React.FC<{ children: ReactNode }> = ({
	children,
}) => {
	const { user } = useAuth();
	const [featureAccess, setFeatureAccess] = useState<Map<string, boolean>>(
		new Map(),
	);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchFeatureAccess = async () => {
		try {
			setLoading(true);
			setError(null);
			const features = await adminAPI.listFeatureAccess();
			const accessMap = new Map<string, boolean>();

			features.forEach((feature) => {
				accessMap.set(feature.feature_name, feature.admin_only);
			});

			setFeatureAccess(accessMap);
		} catch (error) {
			console.error("Failed to fetch feature access settings:", error);
			setError(
				"Failed to load feature permissions. Please refresh the page to try again.",
			);
			// Fail-closed: Clear permissions on error to prevent unauthorized access
			// This ensures that if permissions can't be fetched, users can't access restricted features
			setFeatureAccess(new Map());
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		if (user) {
			fetchFeatureAccess();
		} else {
			setLoading(false);
		}
	}, [user]);

	const canAccessFeature = (featureName: string): boolean => {
		// If not logged in, deny access
		if (!user) return false;

		// Admins can access everything
		if (user.is_admin) return true;

		// Get feature access setting (undefined if not in map)
		const isAdminOnly = featureAccess.get(featureName);

		// If feature doesn't exist in map (undefined), fail closed (deny access)
		// This prevents access if feature access settings haven't loaded or feature is unknown
		if (isAdminOnly === undefined) {
			return false;
		}

		// If admin_only is false, allow access; if true, deny (already checked admin above)
		return !isAdminOnly;
	};

	const isFeatureAdminOnly = (featureName: string): boolean => {
		return featureAccess.get(featureName) || false;
	};

	const refreshFeatureAccess = async () => {
		await fetchFeatureAccess();
	};

	return (
		<FeatureAccessContext.Provider
			value={{
				featureAccess,
				loading,
				error,
				canAccessFeature,
				isFeatureAdminOnly,
				refreshFeatureAccess,
			}}
		>
			{children}
		</FeatureAccessContext.Provider>
	);
};

export const useFeatureAccess = (): FeatureAccessContextType => {
	const context = useContext(FeatureAccessContext);
	if (!context) {
		throw new Error(
			"useFeatureAccess must be used within a FeatureAccessProvider",
		);
	}
	return context;
};
