"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";

const TutorialHelpButton = dynamic(
	() => import("@/tutorial/TutorialHelpButton"),
	{ ssr: false },
);

/** Workflow editor has no AppShell sidebar; show help as an edge button on the right. */
export default function TutorialHelpButtonLoader() {
	const pathname = usePathname();
	if (!pathname?.startsWith("/workflow/")) return null;
	return <TutorialHelpButton mode="edge" />;
}
