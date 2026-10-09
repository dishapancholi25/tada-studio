import type { Metadata } from "next";
import { Geist, Geist_Mono, Inter } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { headers } from "next/headers";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { AuthProvider } from "@/contexts/AuthContext";
import {
  type ColorTheme,
  ColorThemeProvider,
} from "@/contexts/ColorThemeContext";
import { FeatureAccessProvider } from "@/contexts/FeatureAccessContext";
import { GraphProvider } from "@/contexts/GraphContext";
import { LoadingOverlayProvider } from "@/contexts/LoadingOverlayContext";
import { NotificationProvider } from "@/contexts/NotificationContext";
import { OutputSchemaProvider } from "@/contexts/OutputSchemaContext";
import { AccessRequestProvider } from "@/contexts/AccessRequestContext";
import { ToastProvider } from "@/contexts/ToastContext";
import { TutorialProvider } from "@/tutorial/TutorialContext";
import TutorialHelpButtonLoader from "@/tutorial/TutorialHelpButtonLoader";

const geistSans = Geist({
	variable: "--font-geist-sans",
	subsets: ["latin"],
});

const geistMono = Geist_Mono({
	variable: "--font-geist-mono",
	subsets: ["latin"],
});

const inter = Inter({
	variable: "--font-inter",
	subsets: ["latin"],
	weight: ["300", "400", "500", "600", "700"],
	display: "swap",
});

export const metadata: Metadata = {
	title: "TADA Studio",
	description:
		"Drag-and-drop, no-code/low-code platform for creating and executing AI agent workflows using LangGraph and LangChain",
	icons: {
		icon: "/favicon.ico",
		shortcut: "/favicon.ico",
		apple: "/favicon.ico",
	},
};

// Normalise a raw cookie value to a valid ColorTheme on the server side.
// Keeps SSR and client in sync so there is no flash-of-wrong-theme.
function resolveThemeFromCookie(raw: string | undefined): ColorTheme {
	if (raw === "expose" || raw === "plum") return "expose";
	if (raw === "mashreq") return "mashreq";
	// Legacy slug or missing cookie → default to mashreq (white + brand orange).
	return "mashreq";
}

export default async function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	const headerStore = await headers();
	const cookieHeader = headerStore.get("cookie") ?? "";
	const cookieMatch = cookieHeader.match(
		/(?:^|;\s*)agenticstudio-color-theme=([^;]+)/,
	);
	const rawCookieTheme = cookieMatch
		? decodeURIComponent(cookieMatch[1])
		: undefined;
	const initialTheme: ColorTheme = resolveThemeFromCookie(rawCookieTheme);

	return (
		<html lang="en" data-color-theme={initialTheme} suppressHydrationWarning>
			<head>
				{/* Runs before React hydration to stamp data-color-theme on <html>
				    so the first paint uses the correct CSS variable block. */}
				<Script src="/theme-init.js" strategy="beforeInteractive" />
			</head>
			<body
				className={`${inter.variable} ${geistSans.variable} ${geistMono.variable} antialiased`}
			>
				{/* Shown only on /workflow/* routes during SSR hydration */}
				<div id="ssr-workflow-overlay">
					<div
						style={{
							display: "flex",
							flexDirection: "column",
							alignItems: "center",
						}}
					>
						<div className="spinner" />
						<div className="msg">Loading workflow...</div>
					</div>
				</div>
				<ColorThemeProvider initialTheme={initialTheme}>
					<AuthProvider>
						<FeatureAccessProvider>
							<ToastProvider>
								<AccessRequestProvider>
									<NotificationProvider>
										<LoadingOverlayProvider>
											<OutputSchemaProvider>
												<GraphProvider>
													<TutorialProvider>
														<AuthGuard>{children}</AuthGuard>
														<TutorialHelpButtonLoader />
													</TutorialProvider>
												</GraphProvider>
											</OutputSchemaProvider>
										</LoadingOverlayProvider>
									</NotificationProvider>
								</AccessRequestProvider>
							</ToastProvider>
						</FeatureAccessProvider>
					</AuthProvider>
				</ColorThemeProvider>
			</body>
		</html>
	);
}
