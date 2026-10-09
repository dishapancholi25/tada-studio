"use client";

import { Pencil } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useGraph } from "@/contexts/GraphContext";

interface InlineNameEditorProps {
	nodeId: string;
	initialName: string;
	placeholder?: string;
	className?: string;
	editClassName?: string;
	onStartEdit?: () => void;
	onEndEdit?: () => void;
	onSave?: (nodeId: string, newName: string) => Promise<void>;
	readOnly?: boolean;
	showEditIcon?: boolean;
}

export default function InlineNameEditor({
	nodeId,
	initialName,
	placeholder = "Enter name",
	className = "text-sm font-semibold text-white mb-2 truncate",
	editClassName = "",
	onStartEdit,
	onEndEdit,
	onSave,
	readOnly = false,
	showEditIcon = false,
}: InlineNameEditorProps) {
	const [isEditing, setIsEditing] = useState(false);
	const [editValue, setEditValue] = useState(initialName);
	const [displayName, setDisplayName] = useState(initialName);
	const inputRef = useRef<HTMLInputElement>(null);
	const { updateNode } = useGraph();

	// Update display name when initialName changes (from external updates)
	useEffect(() => {
		if (!isEditing) {
			setDisplayName(initialName);
			setEditValue(initialName);
		}
	}, [initialName, isEditing]);

	// Focus input when entering edit mode
	useEffect(() => {
		if (isEditing && inputRef.current) {
			inputRef.current.focus();
			inputRef.current.select();
		}
	}, [isEditing]);

	const handleSave = useCallback(async () => {
		const trimmedValue = editValue.trim();

		// If empty, revert to previous name
		if (!trimmedValue) {
			setEditValue(displayName);
			setIsEditing(false);
			onEndEdit?.();
			return;
		}

		// Only save if value changed
		if (trimmedValue !== displayName) {
			try {
				// Use custom save handler if provided, otherwise use default
				if (onSave) {
					await onSave(nodeId, trimmedValue);
				} else {
					await updateNode(nodeId, { name: trimmedValue });
				}
				setDisplayName(trimmedValue);
			} catch (error) {
				console.error("Failed to update node name:", error);
				// Revert on error
				setEditValue(displayName);
			}
		}

		setIsEditing(false);
		onEndEdit?.();
	}, [editValue, displayName, nodeId, updateNode, onSave, onEndEdit]);

	const handleCancel = useCallback(() => {
		setEditValue(displayName);
		setIsEditing(false);
		onEndEdit?.();
	}, [displayName, onEndEdit]);

	const handleClick = useCallback(
		(e: React.MouseEvent) => {
			if (readOnly || isEditing) {
				return;
			}
			e.stopPropagation(); // Prevent node selection
			setIsEditing(true);
			onStartEdit?.();
		},
		[readOnly, isEditing, onStartEdit],
	);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLInputElement>) => {
			if (e.key === "Enter") {
				e.preventDefault();
				e.stopPropagation();
				void handleSave();
			} else if (e.key === "Escape") {
				e.preventDefault();
				e.stopPropagation();
				handleCancel();
			}
		},
		[handleSave, handleCancel],
	);

	const handleBlur = useCallback(() => {
		void handleSave();
	}, [handleSave]);

	const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
		setEditValue(e.target.value);
	}, []);

	const handleInputClick = useCallback((e: React.MouseEvent) => {
		// Stop propagation to prevent node drag/selection when clicking in edit mode
		e.stopPropagation();
	}, []);

	const handleInputMouseDown = useCallback((e: React.MouseEvent) => {
		// Stop propagation to prevent node drag when clicking in edit mode
		e.stopPropagation();
	}, []);

	if (readOnly) {
		return (
			<h3 className={className} title={displayName || placeholder}>
				{displayName || placeholder}
			</h3>
		);
	}

	if (isEditing) {
		return (
			<input
				ref={inputRef}
				type="text"
				value={editValue}
				onChange={handleChange}
				onKeyDown={handleKeyDown}
				onBlur={handleBlur}
				onClick={handleInputClick}
				onMouseDown={handleInputMouseDown}
				placeholder={placeholder}
				className={`
          ${className}
          ${editClassName}
          w-full px-2 py-1 bg-slate-100 border-2 border-[rgba(var(--color-primary-rgb),0.5)]
          rounded focus:outline-none focus:border-[color:var(--color-primary)]
          transition-colors cursor-text
        `}
			/>
		);
	}

	if (showEditIcon) {
		return (
			<div className="flex items-center gap-2 group/name">
				<h3 className={`${className} cursor-pointer`} onClick={handleClick} title={displayName || placeholder}>
					{displayName || placeholder}
				</h3>
				<button
					onClick={handleClick}
					className="rounded p-1 text-[color:var(--color-text-muted)] opacity-0 group-hover/name:opacity-100 hover:bg-slate-100 hover:text-slate-900 transition-all"
					title="Edit name"
					aria-label="Edit workflow name"
				>
					<Pencil className="w-3.5 h-3.5" />
				</button>
			</div>
		);
	}

	return (
		<h3
			onClick={handleClick}
			className={`${className} cursor-pointer hover:bg-slate-50 border border-slate-200 hover:border-slate-300 rounded px-2 py-1 -mx-2 -my-1 transition-all`}
			title="Click to edit name"
		>
			{displayName || placeholder}
		</h3>
	);
}
