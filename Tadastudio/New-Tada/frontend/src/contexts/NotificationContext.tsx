"use client";

import React, {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useState,
} from "react";
import {
	Notification,
	NotificationContainer,
	type NotificationType,
} from "@/components/ui/Notification";

interface NotificationData {
	id: string;
	type: NotificationType;
	title: string;
	message?: string;
	duration?: number;
}

interface NotificationContextType {
	showNotification: (
		type: NotificationType,
		title: string,
		message?: string,
		duration?: number,
	) => void;
	showSuccess: (title: string, message?: string) => void;
	showError: (title: string, message?: string) => void;
	showWarning: (title: string, message?: string) => void;
	showInfo: (title: string, message?: string) => void;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export function NotificationProvider({ children }: { children: ReactNode }) {
	const [notifications, setNotifications] = useState<NotificationData[]>([]);

	const showNotification = useCallback(
		(
			type: NotificationType,
			title: string,
			message?: string,
			duration?: number,
		) => {
			const id = `${Date.now()}-${Math.random()}`;
			const notification: NotificationData = {
				id,
				type,
				title,
				message,
				duration,
			};

			setNotifications((prev) => [...prev, notification]);
		},
		[],
	);

	const removeNotification = useCallback((id: string) => {
		setNotifications((prev) => prev.filter((n) => n.id !== id));
	}, []);

	const showSuccess = useCallback(
		(title: string, message?: string) => {
			showNotification("success", title, message);
		},
		[showNotification],
	);

	const showError = useCallback(
		(title: string, message?: string) => {
			showNotification("error", title, message);
		},
		[showNotification],
	);

	const showWarning = useCallback(
		(title: string, message?: string) => {
			showNotification("warning", title, message);
		},
		[showNotification],
	);

	const showInfo = useCallback(
		(title: string, message?: string) => {
			showNotification("info", title, message);
		},
		[showNotification],
	);

	const value = {
		showNotification,
		showSuccess,
		showError,
		showWarning,
		showInfo,
	};

	return (
		<NotificationContext.Provider value={value}>
			{children}
			<NotificationContainer>
				{notifications.map((notification) => (
					<Notification
						key={notification.id}
						{...notification}
						onClose={removeNotification}
					/>
				))}
			</NotificationContainer>
		</NotificationContext.Provider>
	);
}

export function useNotification() {
	const context = useContext(NotificationContext);
	if (!context) {
		throw new Error(
			"useNotification must be used within a NotificationProvider",
		);
	}
	return context;
}
