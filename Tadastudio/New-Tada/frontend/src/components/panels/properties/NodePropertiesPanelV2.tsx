"use client";

import {
	ArrowDownToLine,
	Brain,
	FileText,
	Info,
	Layers,
	Pencil,
	Save,
	ShieldCheck,
	Sparkles,
	Trash2,
	X,
} from "lucide-react";
import {
	type ReactNode,
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "react";
import type { Edge, Node } from "reactflow";
import { useNotification } from "@/contexts/NotificationContext";
import { api } from "@/lib/api";
import { getDescendants } from "@/lib/graphUtils";
import {
	type ModelDeploymentOption,
	type ModelLimitsResult,
	modelDeploymentAPI,
} from "@/lib/model-deployment-api";
import type { AgentNodeData } from "@/types/agent";
import { DEFAULT_REVIEW_CONFIG, type ReviewConfig } from "@/types/review";
import MarkdownEditorModal from "../../ui/MarkdownEditorModal";
import type { StructuredOutputSchema } from "../../utils/StructuredOutputBuilder";
import { useGraph } from "@/contexts/GraphContext";
import AssignmentList from "@/components/core/guardrails/AssignmentList";
import EffectiveConfigPreview from "@/components/core/guardrails/EffectiveConfigPreview";
import GuardrailsPanel from "@/components/core/guardrails/GuardrailsPanel";
import PolicyPicker from "@/components/core/guardrails/PolicyPicker";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { invalidateGuardrailStatusCache } from "@/hooks/useNodeGuardrailStatus";
import ConfigSidebar from "./ConfigSidebar";
import CoreConfigSection from "./sections/CoreConfigSection";
import InputSourceSection from "./sections/InputSourceSection";
import MemoryConfigSection from "./sections/MemoryConfigSection";
import OrchestrationSection from "./sections/OrchestrationSection";
import ReviewConfigSection from "./sections/ReviewConfigSection";
import StructuredOutputSection from "./sections/StructuredOutputSection";

interface NodePropertiesPanelProps {
	node: Node;
	onUpdateNode: (nodeId: string, newData: Partial<AgentNodeData>) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
	nodes?: Node[];
	edges?: Edge[];
}

interface ModelOption {
	value: string;
	label: string;
	provider: string;
	providerKey: string;
	description: string;
	model: ModelDeploymentOption;
}

type PanelTabId =
	| "core"
	| "input"
	| "memory"
	| "output"
	| "orchestration"
	| "advanced";

export default function NodePropertiesPanelV2({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
	nodes = [],
	edges = [],
}: NodePropertiesPanelProps) {
	const { currentGraph } = useGraph();
	const [showPolicyPicker, setShowPolicyPicker] = useState(false);
	const [assignmentRefresh, setAssignmentRefresh] = useState(0);
	// State management
	const [agentName, setAgentName] = useState(node.data.name || "");
const [prompt, setPrompt] = useState(
		node.data.agent_config?.system_prompt || node.data.prompt || "",
	);
	const initialModelDeploymentId =
		node.data.agent_config?.llm_config?.model_deployment_id || "";
	const legacyModelName = initialModelDeploymentId
		? ""
		: node.data.agent_config?.llm_config?.model_name || "";
	const [selectedModelId, setSelectedModelId] = useState(
		initialModelDeploymentId,
	);
	const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
	const [modelsLoading, setModelsLoading] = useState(true);
	const [modelLoadError, setModelLoadError] = useState<string | null>(null);

	// Model parameters (agent-level overrides)
	const existingLlmConfig = node.data.agent_config?.llm_config;
	const [modelParams, setModelParams] = useState({
		temperature:
			existingLlmConfig?.temperature != null &&
			existingLlmConfig.temperature !== 0
				? String(existingLlmConfig.temperature)
				: "",
		maxTokens:
			existingLlmConfig?.max_tokens != null
				? String(existingLlmConfig.max_tokens)
				: "",
		topP:
			existingLlmConfig?.top_p != null
				? String(existingLlmConfig.top_p)
				: "",
		reasoningEffort: existingLlmConfig?.reasoning_effort || "",
	});
	const [modelLimits, setModelLimits] = useState<ModelLimitsResult | null>(null);
	const [paramErrors, setParamErrors] = useState<Record<string, string>>({});
	const [isSaving, setIsSaving] = useState(false);
	const [showClearMemoryConfirm, setShowClearMemoryConfirm] = useState(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const [showMarkdownEditor, setShowMarkdownEditor] = useState(false);
	const [activeTab, setActiveTab] = useState<PanelTabId>("core");
	const [isEditingName, setIsEditingName] = useState(false);
	const nameInputRef = useRef<HTMLInputElement>(null);

	// Track initial values for unsaved changes detection
	const initialValues = useRef({
		name: node.data.name || "",
prompt:
			node.data.agent_config?.system_prompt || node.data.prompt || "",
		modelId: initialModelDeploymentId,
		memoryEnabled: node.data.agent_config?.memory_enabled || false,
		memoryWindowSize: node.data.agent_config?.memory_window_size || 10,
		memoryStrategy:
			node.data.agent_config?.memory_strategy || "thread_scoped",
	});

	// Check if this is a sub-agent or special node type
	const isSubAgent = node.data.isSubAgent || node.data.is_sub_agent || false;
	const isStartNode =
		node.data.node_type === "START" || node.data.type === "START";
	const isEndNode = node.data.node_type === "END" || node.data.type === "END";
	const isAgentNode =
		node.data.node_type === "AGENT" || node.data.type === "AGENT";
	const isSpecialNode = isStartNode || isEndNode;

	// Delegation description for sub-agents
	const [delegationDescription, setDelegationDescription] = useState(
		node.data.delegation_description || node.data.delegationDescription || "",
	);

	// Memory configuration
	const [memoryEnabled, setMemoryEnabled] = useState(
		node.data.agent_config?.memory_enabled || false,
	);
	const [memoryWindowSize, setMemoryWindowSize] = useState(
		node.data.agent_config?.memory_window_size || 10,
	);
	const [memoryStrategy, setMemoryStrategy] = useState(
		node.data.agent_config?.memory_strategy || "thread_scoped",
	);
	const [clearingMemory, setClearingMemory] = useState(false);

	// Guardrails toggle
	const [guardrailsEnabled, setGuardrailsEnabled] = useState(
		node.data.agent_config?.guardrails_enabled !== false,
	);

	const { showSuccess, showError } = useNotification();

	// Structured output configuration
	const [enableStructuredOutput, setEnableStructuredOutput] = useState(
		(node.data.agent_config?.structured_outputs || []).length > 0,
	);
	const [structuredOutputs, setStructuredOutputs] = useState<
		StructuredOutputSchema[]
	>(node.data.agent_config?.structured_outputs || []);

	// Orchestrator configuration — derived live from edges so the panel stays
	// in sync when delegation connections are added/removed without remounting.
	const isOrchestrator = useMemo(
		() =>
			edges.some(
				(edge) =>
					edge.source === node.id &&
					edge.data?.connection_type === "delegation",
			) ||
			node.data.agent_config?.is_orchestrator ||
			false,
		[edges, node.id, node.data.agent_config?.is_orchestrator],
	);
	const [orchestratorMode] = useState(
		node.data.agent_config?.orchestrator_mode || "supervisor",
	);
	const delegatedAgents = useMemo(
		() =>
			edges
				.filter(
					(edge) =>
						edge.source === node.id &&
						edge.data?.connection_type === "delegation",
				)
				.map((edge) => edge.target),
		[edges, node.id],
	);

	// Sub-agent delegation descriptions (for orchestrators)
	const [subAgentDelegationDescriptions, setSubAgentDelegationDescriptions] =
		useState<Record<string, string>>({});
	const [inputSourceConfig, setInputSourceConfig] = useState<any>(
		node.data.input_source_config || null,
	);

	// Review configuration
	const [reviewConfig, setReviewConfig] = useState<ReviewConfig>(() => {
		const existingConfig = node.data.agent_config?.review_config;
		if (existingConfig) {
			return { ...DEFAULT_REVIEW_CONFIG, ...existingConfig };
		}
		return DEFAULT_REVIEW_CONFIG;
	});


	useEffect(() => {
		const fetchModels = async () => {
			try {
				setModelsLoading(true);
				setModelLoadError(null);
				const deployments = await modelDeploymentAPI.listSelectOptions();
				// Filter to only show LLM models (exclude embedding models)
				const llmDeployments = deployments.filter(
					(d) => d.model_type === "llm",
				);
				const providerLabels: Record<string, string> = {
					azure_openai: "Azure OpenAI",
					openai: "OpenAI",
					anthropic: "Anthropic",
				};

				const mapped: ModelOption[] = llmDeployments
					.map((deployment) => {
						const providerLabel =
							providerLabels[deployment.provider] || deployment.provider;

						const descriptionParts = [providerLabel, deployment.model_name];

						return {
							value: deployment.id,
							label: deployment.display_name || deployment.name,
							provider: providerLabel,
							providerKey: deployment.provider,
							description: descriptionParts.join(" • "),
							model: deployment,
						};
					})
					.sort((a, b) => a.label.localeCompare(b.label));

				setModelOptions(mapped);

				if (
					!initialModelDeploymentId &&
					!legacyModelName &&
					mapped.length > 0
				) {
					const defaultOption =
						mapped.find((option) => option.model.is_default) || mapped[0];
					setSelectedModelId(defaultOption.value);
				}
			} catch (err) {
				setModelLoadError(
					err instanceof Error
						? err.message
						: "Failed to load model deployments",
				);
			} finally {
				setModelsLoading(false);
			}
		};

		void fetchModels();
	}, [initialModelDeploymentId, legacyModelName]);

	// Fetch model limits when selected model changes
	useEffect(() => {
		const selected = modelOptions.find((o) => o.value === selectedModelId);
		if (!selected) {
			setModelLimits(null);
			return;
		}
		let cancelled = false;
		const fetchLimits = async () => {
			try {
				const result = await modelDeploymentAPI.lookupModelLimits(selected.model.model_name);
				if (!cancelled) setModelLimits(result);
			} catch {
				if (!cancelled) setModelLimits(null);
			}
		};
		void fetchLimits();
		return () => { cancelled = true; };
	}, [selectedModelId, modelOptions]);

	// Load sub-agent delegation descriptions for orchestrators
	useEffect(() => {
		if (isOrchestrator && delegatedAgents.length > 0) {
			const descriptions: Record<string, string> = {};
			delegatedAgents.forEach((agentId) => {
				const subAgent = nodes.find((n) => n.id === agentId);
				if (subAgent) {
					descriptions[agentId] = subAgent.data.delegation_description || subAgent.data.delegationDescription || "";
				}
			});
			setSubAgentDelegationDescriptions(descriptions);
		}
	}, [isOrchestrator, delegatedAgents, nodes]);

	useEffect(() => {
		setInputSourceConfig(node.data.input_source_config || null);
	}, [node.id]);

	useEffect(() => {
		setActiveTab("core");
	}, [node.id]);

	useEffect(() => {
		if (isEditingName && nameInputRef.current) {
			nameInputRef.current.focus();
			nameInputRef.current.select();
		}
	}, [isEditingName]);

const availableInputNodes = useMemo(() => {
		if (!nodes || !edges) return [];

		// Get all descendants of the current node to avoid cycles
		const descendants = getDescendants(node.id, edges);

		// Filter nodes:
		// 1. Must not be the current node (self)
		// 2. Must not be a descendant (avoid cycles)
		// 3. Must be a valid input type (Agent, Start, etc.) - though usually we allow most nodes as input
		// 4. Should we allow End nodes? Probably not as input.

		const candidates = nodes.filter((candidate) => {
			// Exclude self
			if (candidate.id === node.id) return false;

			// Exclude descendants
			if (descendants.has(candidate.id)) return false;

			// Exclude End nodes (they don't produce output for other nodes usually)
			if (candidate.type === "endNode" || candidate.data?.type === "END")
				return false;

			return true;
		});

		// Sort by position (top-to-bottom, left-to-right)
		return candidates.sort((a, b) => {
			// If y difference is significant, sort by y
			if (Math.abs(a.position.y - b.position.y) > 50) {
				return a.position.y - b.position.y;
			}
			// Otherwise sort by x
			return a.position.x - b.position.x;
		});
	}, [edges, node.id, nodes]);

	const effectiveInputConfig =
		inputSourceConfig ?? node.data.input_source_config;
	const inputSourceMode = effectiveInputConfig?.source_mode || "previous";
	const hasCustomInputConfig =
		!!effectiveInputConfig &&
		(effectiveInputConfig.source_mode !== "previous" ||
			effectiveInputConfig.include_original_input ||
			(effectiveInputConfig.source_node_ids?.length ?? 0) > 0 ||
			(effectiveInputConfig.selected_fields?.length ?? 0) > 0 ||
			Boolean(effectiveInputConfig.custom_template));

	const panelTabs = useMemo(() => {
		const tabs: Array<{
			id: PanelTabId;
			label: string;
			description?: string;
			icon: ReactNode;
			accent:
				| "core"
				| "input"
				| "memory"
				| "output"
				| "orchestration"
				| "advanced";
		}> = [
			{
				id: "core",
				label: "Core",
				description: "Model & prompt",
				icon: <Sparkles className="h-4 w-4" />,
				accent: "core",
			},
		];

		if (isAgentNode) {
			tabs.push(
				{
					id: "input",
					label: "Input",
					description: "Context intake",
					icon: <ArrowDownToLine className="h-4 w-4" />,
					accent: "input",
				},
				{
					id: "memory",
					label: "Memory",
					description: "Conversation memory",
					icon: <Brain className="h-4 w-4" />,
					accent: "memory",
				},
				{
					id: "output",
					label: "Output",
					description: "Response format",
					icon: <FileText className="h-4 w-4" />,
					accent: "output",
				},
				{
					id: "advanced",
					label: "Guardrails",
					description: "Safety policies",
					icon: <ShieldCheck className="h-4 w-4" />,
					accent: "advanced",
				},
			);
		}

		if (isOrchestrator || isSubAgent) {
			tabs.push({
				id: "orchestration",
				label: "Orchestration",
				description: isOrchestrator ? "Delegate teammates" : "Delegation role",
				icon: <Layers className="h-4 w-4" />,
				accent: "orchestration",
			});
		}

		return tabs;
	}, [isAgentNode, isOrchestrator, isSubAgent]);

	useEffect(() => {
		if (
			!panelTabs.some((tab) => tab.id === activeTab) &&
			panelTabs.length > 0
		) {
			setActiveTab(panelTabs[0].id);
		}
	}, [activeTab, panelTabs]);

	const handleInputSourceUpdate = useCallback(
		(config: any) => {
			const shouldPersist =
				config?.source_mode !== "previous" ||
				config?.include_original_input ||
				(config?.source_node_ids?.length ?? 0) > 0 ||
				(config?.selected_fields?.length ?? 0) > 0 ||
				Boolean(config?.custom_template);

			// Always update local state to reflect changes immediately
			// This prevents falling back to stale node.data while the update is in flight
			const normalized = {
				...config,
				source_node_ids: config?.source_node_ids
					? [...config.source_node_ids]
					: [],
				selected_fields: config?.selected_fields
					? [...config.selected_fields]
					: [],
			};
			setInputSourceConfig(normalized);

			if (shouldPersist) {
				void onUpdateNode(node.id, { input_source_config: normalized as any });
			} else {
				void onUpdateNode(node.id, { input_source_config: null as any });
			}
		},
		[node.id, onUpdateNode],
	);

	const handleClearMemory = () => {
		setShowClearMemoryConfirm(true);
	};

	const handleConfirmClearMemory = async () => {
		setClearingMemory(true);
		try {
			const result = await api.clearAgentMemory(node.id);
			// console.log('Memory cleared:', result);

			showSuccess(
				"Memory Cleared",
				result.message ||
					`Successfully cleared memory for agent ${node.data.name || "Agent"}`,
			);
		} catch (error) {
			// console.error('Failed to clear memory:', error);
			showError("Error", "Failed to clear agent memory");
		} finally {
			setClearingMemory(false);
		}
	};
	const handleSave = async () => {
		setIsSaving(true);
		try {
			const selectedOption = modelOptions.find(
				(option) => option.value === selectedModelId,
			);
			const existingLlmConfig = node.data.agent_config?.llm_config;

			if (!selectedOption && !legacyModelName) {
				if (modelOptions.length === 0) {
					showError(
						"No Models Configured",
						"Add a model deployment in Settings → LLM Providers before saving.",
					);
				} else {
					showError(
						"Model Required",
						"Select one of the configured models before saving this agent.",
					);
				}
				setIsSaving(false);
				return;
			}

			// Validate model parameters (matching LLM provider validation)
			const errors: Record<string, string> = {};
			if (modelParams.temperature) {
				const temp = Number(modelParams.temperature);
				if (temp < 0 || temp > 2) {
					errors.temperature = "Temperature must be between 0 and 2";
				}
			}
			if (modelParams.topP) {
				const topP = Number(modelParams.topP);
				if (topP < 0 || topP > 1) {
					errors.topP = "Top P must be between 0 and 1";
				}
			}
			if (modelParams.maxTokens) {
				const maxTokens = Number(modelParams.maxTokens);
				if (maxTokens <= 0) {
					errors.maxTokens = "Max tokens must be a positive number";
				} else if (modelLimits?.max_output_tokens && maxTokens > modelLimits.max_output_tokens) {
					errors.maxTokens = `Exceeds model limit of ${modelLimits.max_output_tokens.toLocaleString()} output tokens`;
				}
			}
			if (Object.keys(errors).length > 0) {
				setParamErrors(errors);
				setActiveTab("core");
				setIsSaving(false);
				return;
			}
			setParamErrors({});

			let llmConfig: any;
			if (selectedOption) {
				const deployment = selectedOption.model;

				// Resolve temperature: explicit agent value > deployment default > provider fallback
				const agentTemp = modelParams.temperature
					? Number.parseFloat(modelParams.temperature)
					: null;
				const deploymentTemp = deployment.default_temperature != null
					? Number(deployment.default_temperature)
					: null;
				const temperature = agentTemp ?? deploymentTemp ?? 0;

				// Resolve max tokens: explicit agent value > deployment default > none
				const agentMaxTokens = modelParams.maxTokens
					? Number.parseInt(modelParams.maxTokens, 10)
					: null;

				// Resolve top_p: explicit agent value > deployment default > none
				const agentTopP = modelParams.topP
					? Number.parseFloat(modelParams.topP)
					: null;

				// Resolve reasoning effort: explicit agent value > deployment default > none
				const agentReasoning = modelParams.reasoningEffort || null;

				// Sensitive provider configuration (api_base, api_version,
				// deployment_name, credentials) is intentionally NOT sent from
				// the client. The backend enriches these from the deployment
				// record at execution time using model_deployment_id.
				llmConfig = {
					provider: deployment.provider,
					model_name: deployment.model_name,
					temperature,
					api_key_env_var: "MODEL_DEPLOYMENT",
					base_url_env_var: "MODEL_DEPLOYMENT",
					model_deployment_id: deployment.id,
					display_name: deployment.display_name || deployment.name,
					supports_function_calling: true,
					supports_streaming: true,
					timeout: existingLlmConfig?.timeout ?? 30,
					organization_id: existingLlmConfig?.organization_id || null,
				};

				// Save explicit agent overrides; send null to clear previously
				// stored values so the backend deep-merge removes the key and
				// deployment defaults are resolved at execution time instead.
				if (agentMaxTokens != null) {
					llmConfig.max_tokens = agentMaxTokens;
				} else if (existingLlmConfig?.max_tokens != null) {
					// User cleared the field — explicitly null out the stored value
					llmConfig.max_tokens = null;
				}
				if (agentTopP != null) {
					llmConfig.top_p = agentTopP;
				} else if (existingLlmConfig?.top_p != null) {
					llmConfig.top_p = null;
				}
				if (agentReasoning) {
					llmConfig.reasoning_effort = agentReasoning;
				} else if (existingLlmConfig?.reasoning_effort) {
					llmConfig.reasoning_effort = null;
				}
			} else {
				llmConfig = existingLlmConfig;
			}

			if (!llmConfig) {
				showError(
					"Model Required",
					"Unable to determine model configuration for this agent.",
				);
				setIsSaving(false);
				return;
			}

			const agentConfig = {
				...node.data.agent_config,
				system_prompt: prompt,
				memory_enabled: memoryEnabled,
				memory_window_size: memoryWindowSize,
				memory_strategy: memoryStrategy,
				structured_outputs: enableStructuredOutput ? structuredOutputs : [],
				llm_config: llmConfig,
				review_config: reviewConfig.review_enabled ? reviewConfig : null,
				guardrails_enabled: guardrailsEnabled,
			};

			onUpdateNode(node.id, {
				name: agentName,
agent_config: agentConfig,
				delegation_description: isSubAgent ? delegationDescription : undefined,
				...(inputSourceConfig
					? { input_source_config: inputSourceConfig }
					: { input_source_config: null }),
			} as any);

			// Update sub-agent delegation descriptions if this is an orchestrator
			if (
				isOrchestrator &&
				Object.keys(subAgentDelegationDescriptions).length > 0
			) {
				for (const [agentId, description] of Object.entries(
					subAgentDelegationDescriptions,
				)) {
					onUpdateNode(agentId, {
						delegation_description: description,
					});
				}
			}

			// Show success feedback
			onClose();
		} catch (error) {
			// console.error('Failed to save node:', error);
		} finally {
			setIsSaving(false);
		}
	};

	const handleDelete = () => {
		if (isStartNode) {
			showError(
				"Start node required",
				"Every workflow begins with a Start node, so it stays in place.",
			);
			return;
		}

		setShowDeleteConfirm(true);
	};

	const handleConfirmDelete = () => {
		onDeleteNode(node.id);
		onClose();
	};

	const isTutorialLocked = useCallback(
		() => document.body.dataset.tutorialLockPanel === "true",
		[],
	);

	const handleBackdropClick = useCallback(() => {
		if (isTutorialLocked()) return;
		onClose();
	}, [onClose, isTutorialLocked]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleExpandMarkdownEditor = useCallback(() => {
		setShowMarkdownEditor(true);
	}, []);

	const handleCloseMarkdownEditor = useCallback(() => {
		setShowMarkdownEditor(false);
	}, []);

	const handleMarkdownSave = useCallback((newContent: string) => {
		setPrompt(newContent);
		setShowMarkdownEditor(false);
	}, []);

	// Unsaved changes detection
	const hasUnsavedChanges = useMemo(() => {
		const init = initialValues.current;
		return (
			agentName !== init.name ||
			prompt !== init.prompt ||
			selectedModelId !== init.modelId ||
			memoryEnabled !== init.memoryEnabled ||
			memoryWindowSize !== init.memoryWindowSize ||
			memoryStrategy !== init.memoryStrategy
		);
	}, [
		agentName,
		prompt,
		selectedModelId,
		memoryEnabled,
		memoryWindowSize,
		memoryStrategy,
	]);

	// Keyboard shortcut: Cmd/Ctrl+S to save
	const handleSaveRef = useRef(handleSave);
	handleSaveRef.current = handleSave;

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === "s") {
				e.preventDefault();
				handleSaveRef.current();
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, []);

	// Responsive sidebar collapse
	const contentRef = useRef<HTMLDivElement>(null);
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

	useEffect(() => {
		const el = contentRef.current;
		if (!el || typeof ResizeObserver === "undefined") return;
		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				setSidebarCollapsed(entry.contentRect.width < 400);
			}
		});
		observer.observe(el);
		return () => observer.disconnect();
	}, []);

	return (
		<div
			data-tutorial="config-sidebar"
			className={`fixed inset-0 z-[110] flex items-start justify-center px-4 pt-[5vh] pb-4 animate-fadeIn ${
				showMarkdownEditor ? "backdrop-blur-md" : "backdrop-blur-xl"
			}`}
			style={
				showMarkdownEditor
					? {
							background:
								"radial-gradient(ellipse at center, rgba(var(--color-primary-rgb), 0.08) 0%, transparent 58%), rgba(51, 65, 85, 0.36)",
						}
					: {
							background:
								"radial-gradient(ellipse at center, rgba(var(--color-primary-rgb), 0.04) 0%, transparent 60%), rgba(0,0,0,0.7)",
						}
			}
			onClick={handleBackdropClick}
		>
			<div
				className="w-[70vw] max-w-[1100px]"
				onClick={handleStopPropagation}
			>
			<div>
			<div
				className={`relative flex flex-col overflow-hidden min-h-[320px] rounded-[4px] border border-slate-200 bg-white shadow-sm transition-[max-height] duration-200 max-h-[80vh] ${
					showMarkdownEditor ? "bg-white/95 backdrop-blur-md" : ""
				}`}
			>
				{/* Header — Workflow Management style */}
				<div className="relative flex-none rounded-t-[4px] border-b border-slate-200 bg-white">
					<div className="flex items-start justify-between gap-4 px-6 pt-5 pb-4">
						<div className="flex items-start gap-3 min-w-0">
							<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
								{isSpecialNode ? (
									<Info className="h-5 w-5 text-orange-600" />
								) : (
									<Brain className="h-5 w-5 text-orange-600" />
								)}
							</div>
							<div className="min-w-0 flex-1">
								{isSpecialNode ? (
									<>
										<h2 className="text-lg font-semibold text-slate-900 tracking-tight">
											Node Configuration
										</h2>
										<p className="mt-0.5 text-xs text-slate-500">
											Start or end node settings
										</p>
									</>
								) : (
									<>
										<div className="flex flex-wrap items-center gap-x-2 gap-y-1">
											{isEditingName ? (
												<input
													ref={nameInputRef}
													type="text"
													value={agentName}
													onChange={(e) => setAgentName(e.target.value)}
													onBlur={() => setIsEditingName(false)}
													onKeyDown={(e) => {
														if (e.key === "Enter" || e.key === "Escape") {
															e.preventDefault();
															setIsEditingName(false);
														}
													}}
													className="min-w-0 max-w-full rounded-[4px] border border-slate-200 bg-white px-2 py-1 text-lg font-semibold text-slate-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
													placeholder="Agent Name"
												/>
											) : (
												<button
													type="button"
													onClick={() => setIsEditingName(true)}
													className="group/edit flex min-w-0 max-w-full items-center gap-2 rounded-[4px] border border-transparent px-2 py-1 text-left transition-colors hover:border-orange-400 hover:bg-slate-50"
													title="Click to rename"
												>
													<span className="truncate text-lg font-semibold text-slate-900">
														{agentName || "Unnamed Agent"}
													</span>
													<Pencil className="h-3.5 w-3.5 shrink-0 text-slate-400 transition-colors group-hover/edit:text-orange-600" />
												</button>
											)}
											<span className="text-sm font-medium text-slate-500 whitespace-nowrap">
												· Configuration
											</span>
										</div>
										<p className="mt-1 text-xs text-slate-500">
											Model, prompt, memory, and guardrails
										</p>
									</>
								)}
							</div>
						</div>
						<button
							type="button"
							onClick={() => { if (!isTutorialLocked()) onClose(); }}
							className="shrink-0 rounded-[4px] border border-slate-200 bg-white p-1.5 text-slate-500 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
						>
							<X className="h-4 w-4" />
						</button>
					</div>
				</div>

				{/* Content */}
				<div
					ref={contentRef}
					className="flex-1 flex min-h-0 overflow-hidden relative"
				>
					{/* Sidebar */}
					{!isSpecialNode && panelTabs.length > 0 && (
						<ConfigSidebar
							items={panelTabs}
							activeItem={activeTab}
							onChange={(id) => setActiveTab(id as PanelTabId)}
							collapsed={sidebarCollapsed}
							variant="light"
						/>
					)}

					{/* Section content */}
					<div
						className={`flex-1 overflow-y-auto px-6 py-4 ${
							showMarkdownEditor ? "bg-slate-50/90" : "bg-white"
						}`}
					>
						{/* Special node message */}
						{isSpecialNode && (
							<div className="rounded-[4px] border border-slate-200 bg-slate-50 p-5 flex items-start gap-3 shadow-sm">
								<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100 text-orange-600">
									<Info className="h-5 w-5" />
								</div>
								<div className="min-w-0">
									<h4 className="text-sm font-semibold text-slate-900">
										{isStartNode
											? "Workflow Entry Point"
											: "Workflow Exit Point"}
									</h4>
									<p className="text-xs text-slate-600 mt-1">
										{isStartNode
											? "This node receives initial input when the workflow begins"
											: "This node collects and returns the final output of the workflow"}
									</p>
								</div>
							</div>
						)}

						{/* Tab content */}
						{!isSpecialNode && (
							<div>
								{activeTab === "core" && (
									<CoreConfigSection
										selectedModelId={selectedModelId}
										onModelChange={setSelectedModelId}
										prompt={prompt}
										onPromptChange={setPrompt}
										onExpandMarkdownEditor={handleExpandMarkdownEditor}
										modelOptions={modelOptions}
										modelsLoading={modelsLoading}
										modelLoadError={modelLoadError}
										legacyModelName={legacyModelName}
										modelParams={modelParams}
										onModelParamsChange={setModelParams}
										dropdownMenuAppearance="light"
										deploymentDefaults={(() => {
											const selected = modelOptions.find(
												(o) => o.value === selectedModelId,
											);
											if (!selected) return undefined;
											const m = selected.model;
											return {
												temperature: m.default_temperature ?? null,
												maxTokens: m.default_max_tokens ?? null,
												topP: m.default_top_p ?? null,
												reasoningEffort: m.default_reasoning_effort ?? null,
											};
										})()}
									validationErrors={paramErrors}
									/>
								)}

								{activeTab === "input" && isAgentNode && (
									<InputSourceSection
										node={node}
										availableNodes={availableInputNodes}
										onUpdate={handleInputSourceUpdate}
										hasCustomConfig={hasCustomInputConfig}
										currentConfig={effectiveInputConfig}
										edges={edges}
									/>
								)}

								{activeTab === "memory" && (
									<MemoryConfigSection
										memoryEnabled={memoryEnabled}
										onMemoryEnabledChange={setMemoryEnabled}
										memoryWindowSize={memoryWindowSize}
										onMemoryWindowSizeChange={setMemoryWindowSize}
										memoryStrategy={memoryStrategy}
										onMemoryStrategyChange={setMemoryStrategy}
										onClearMemory={handleClearMemory}
										clearingMemory={clearingMemory}
										agentName={node.data.name || "Agent"}
										dropdownMenuAppearance="light"
									/>
								)}

								{activeTab === "output" && (
									<StructuredOutputSection
										enableStructuredOutput={enableStructuredOutput}
										onEnableStructuredOutputChange={setEnableStructuredOutput}
										structuredOutputs={structuredOutputs}
										onStructuredOutputsChange={setStructuredOutputs}
									/>
								)}

								{activeTab === "orchestration" &&
									(isOrchestrator || isSubAgent) && (
										<OrchestrationSection
											isOrchestrator={isOrchestrator}
											isSubAgent={isSubAgent}
											orchestratorMode={orchestratorMode}
											delegatedAgents={delegatedAgents}
											nodes={nodes}
											subAgentDelegationDescriptions={
												subAgentDelegationDescriptions
											}
											onSubAgentDelegationDescriptionsChange={
												setSubAgentDelegationDescriptions
											}
											delegationDescription={delegationDescription}
											onDelegationDescriptionChange={setDelegationDescription}
										/>
									)}

								{activeTab === "advanced" && isAgentNode && (
									<div className="space-y-8">
										<ReviewConfigSection
											reviewConfig={reviewConfig}
											onReviewConfigChange={setReviewConfig}
											modelOptions={modelOptions}
											modelsLoading={modelsLoading}
											dropdownMenuAppearance="light"
										/>
										{/* Guardrails toggle + assignments */}
										<GuardrailsPanel
											theme="light"
											enabled={guardrailsEnabled}
											onToggle={setGuardrailsEnabled}
											onAssign={() => setShowPolicyPicker(true)}
											description="Enforce safety policies on this agent's inputs, outputs, and tool usage."
										>
											<AssignmentList
												targetType="agent_node"
												targetId={node.id}
												workflowId={currentGraph?.workflow_id}
												onOpenPolicyPicker={() => setShowPolicyPicker(true)}
												refreshTrigger={assignmentRefresh}
												hideHeader
											/>
											<EffectiveConfigPreview
												workflowId={currentGraph?.workflow_id}
												nodeId={node.id}
												refreshTrigger={assignmentRefresh}
											/>
										</GuardrailsPanel>
									</div>
								)}
							</div>
						)}
					</div>

					</div>

				{/* Footer */}
				<div className="border-t border-slate-200 bg-white px-6 py-3 rounded-b-[4px]">
					<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
						<button
							onClick={handleDelete}
							disabled={isStartNode}
							className={`px-3 py-2 rounded-[4px] transition-all flex items-center gap-1.5 border text-xs ${
								isStartNode
									? "bg-slate-50 text-slate-400 border-slate-200 cursor-not-allowed opacity-80"
									: "bg-white text-red-600 border-slate-200 hover:border-red-300 hover:bg-red-50 hover:text-red-700"
							}`}
							title={
								isStartNode
									? "The Start node anchors the workflow and cannot be removed."
									: undefined
							}
						>
							<Trash2
								className={`w-3.5 h-3.5 ${isStartNode ? "text-slate-400" : ""}`}
							/>
							{isStartNode ? "Start Node Locked" : "Delete Node"}
						</button>

						<div className="flex items-center gap-3 sm:ml-auto">
							{hasUnsavedChanges && (
								<span className="flex items-center gap-1.5 text-[11px] text-slate-500">
									<span className="h-1.5 w-1.5 rounded-full bg-orange-500 animate-smoothPulse" />
									Unsaved
								</span>
							)}
							<span className="text-[11px] text-slate-400 hidden sm:inline">
								Ctrl/⌘ + S to save
							</span>
							<button
								onClick={() => { if (!isTutorialLocked()) onClose(); }}
								className="px-4 py-2 rounded-[4px] border border-slate-200 bg-white text-xs font-medium text-slate-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20"
							>
								Cancel
							</button>
							<button
								data-tutorial="config-save-btn"
								onClick={handleSave}
								disabled={isSaving}
								className="px-5 py-2 rounded-[4px] text-xs font-semibold text-white bg-orange-500 border border-orange-500 transition-colors hover:bg-orange-600 hover:border-orange-600 disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30"
							>
								{isSaving ? (
									<span className="inline-flex items-center gap-1.5">
										<span className="h-3.5 w-3.5 border-2 border-current/20 border-t-current rounded-full animate-spin" />
										Saving...
									</span>
								) : (
									<span className="inline-flex items-center gap-1.5">
										<Save className="w-3.5 h-3.5" />
										Save Changes
									</span>
								)}
							</button>
						</div>
					</div>
				</div>

				{/* Policy picker overlay — covers entire modal */}
				{showPolicyPicker && (
					<PolicyPicker
						targetType="agent_node"
						targetId={node.id}
						workflowId={currentGraph?.workflow_id}
						onAssigned={() => { setShowPolicyPicker(false); setAssignmentRefresh((c) => c + 1); invalidateGuardrailStatusCache(currentGraph?.workflow_id); }}
						onClose={() => setShowPolicyPicker(false)}
					/>
				)}
			</div>
			</div>
			</div>
			{/* Markdown Editor Modal */}
			<MarkdownEditorModal
				isOpen={showMarkdownEditor}
				onClose={handleCloseMarkdownEditor}
				onSave={handleMarkdownSave}
				initialContent={prompt}
				title="Edit System Prompt"
				placeholder="Define your agent's role and instructions...

Example:
# Role
You are an expert data analyst specialized in...

## Instructions
- Analyze data thoroughly
- Provide clear explanations
- Use visualizations when helpful

## Guidelines
Always ensure accuracy and cite sources when relevant."
			/>
			<ConfirmDialog
				isOpen={showClearMemoryConfirm}
				onClose={() => setShowClearMemoryConfirm(false)}
				onConfirm={handleConfirmClearMemory}
				title="Clear Memory"
				message="Are you sure you want to clear all memory for this agent? This action cannot be undone."
				confirmText="Clear"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>
			<ConfirmDialog
				isOpen={showDeleteConfirm}
				onClose={() => setShowDeleteConfirm(false)}
				onConfirm={handleConfirmDelete}
				title="Delete Node"
				message="Are you sure you want to delete this node? This action cannot be undone."
				confirmText="Delete"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>
		</div>
	);
}
