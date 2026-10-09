"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CompliancePage() {
	const router = useRouter();

	useEffect(() => {
		router.replace("/guardrails");
	}, [router]);

	return null;
}
