"use client";

import type { WorkflowTemplateGraphDefinition } from "@/types/library";

const CONTEXT_STORAGE_KEY = "agentTemplateInsertContext";
const PAYLOAD_STORAGE_KEY = "agentTemplateInsertPayload";

export interface AgentTemplateInsertContext {
	workflowId: string;
	graphName: string;
	returnPath: string;
	sourceNodeId?: string | null;
	sourceHandle?: string | null;
	insertionPosition?: { x: number; y: number };
	createdAt: number;
}

export interface AgentTemplateInsertPayload {
	templateId: string;
	templateName: string;
	graphDefinition: WorkflowTemplateGraphDefinition;
	primaryAgentNodeId?: string | null;
	storedAt: number;
}

const isBrowser = () =>
	typeof window !== "undefined" && typeof window.sessionStorage !== "undefined";

function safeParse<T>(value: string | null): T | null {
	if (!value) return null;
	try {
		return JSON.parse(value) as T;
	} catch {
		return null;
	}
}

export function setAgentTemplateInsertContext(
	context: AgentTemplateInsertContext,
): void {
	if (!isBrowser()) return;
	sessionStorage.setItem(CONTEXT_STORAGE_KEY, JSON.stringify(context));
}

export function getAgentTemplateInsertContext(): AgentTemplateInsertContext | null {
	if (!isBrowser()) return null;
	return safeParse<AgentTemplateInsertContext>(
		sessionStorage.getItem(CONTEXT_STORAGE_KEY),
	);
}

export function clearAgentTemplateInsertContext(): void {
	if (!isBrowser()) return;
	sessionStorage.removeItem(CONTEXT_STORAGE_KEY);
}

export function setAgentTemplateInsertPayload(
	payload: AgentTemplateInsertPayload,
): void {
	if (!isBrowser()) return;
	sessionStorage.setItem(PAYLOAD_STORAGE_KEY, JSON.stringify(payload));
}

export function getAgentTemplateInsertPayload(): AgentTemplateInsertPayload | null {
	if (!isBrowser()) return null;
	return safeParse<AgentTemplateInsertPayload>(
		sessionStorage.getItem(PAYLOAD_STORAGE_KEY),
	);
}

export function clearAgentTemplateInsertPayload(): void {
	if (!isBrowser()) return;
	sessionStorage.removeItem(PAYLOAD_STORAGE_KEY);
}
