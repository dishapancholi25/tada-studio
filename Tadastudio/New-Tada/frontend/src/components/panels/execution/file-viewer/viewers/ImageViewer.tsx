"use client";

import {
	Maximize2,
	Minimize2,
	Minus,
	Move,
	Plus,
	RotateCcw,
	ZoomIn,
} from "lucide-react";
import { useState, useCallback, useRef, useEffect } from "react";
import type { ImageViewerProps } from "../types/fileViewer.types";

export default function ImageViewer({ src, alt, filename }: ImageViewerProps) {
	const [scale, setScale] = useState(1);
	const [position, setPosition] = useState({ x: 0, y: 0 });
	const [isDragging, setIsDragging] = useState(false);
	const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
	const [imageLoaded, setImageLoaded] = useState(false);
	const [imageError, setImageError] = useState(false);
	const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
	const containerRef = useRef<HTMLDivElement>(null);

	const MIN_SCALE = 0.1;
	const MAX_SCALE = 5;
	const ZOOM_STEP = 0.25;

	const handleZoomIn = useCallback(() => {
		setScale((prev) => Math.min(prev + ZOOM_STEP, MAX_SCALE));
	}, []);

	const handleZoomOut = useCallback(() => {
		setScale((prev) => Math.max(prev - ZOOM_STEP, MIN_SCALE));
	}, []);

	const handleReset = useCallback(() => {
		setScale(1);
		setPosition({ x: 0, y: 0 });
	}, []);

	const handleFitToWindow = useCallback(() => {
		if (!containerRef.current || !naturalSize.width) return;

		const container = containerRef.current;
		const containerWidth = container.clientWidth - 48; // Padding
		const containerHeight = container.clientHeight - 48;

		const scaleX = containerWidth / naturalSize.width;
		const scaleY = containerHeight / naturalSize.height;
		const newScale = Math.min(scaleX, scaleY, 1);

		setScale(newScale);
		setPosition({ x: 0, y: 0 });
	}, [naturalSize]);

	// Handle wheel zoom
	const handleWheel = useCallback(
		(e: React.WheelEvent) => {
			e.preventDefault();
			const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
			setScale((prev) =>
				Math.min(Math.max(prev + delta, MIN_SCALE), MAX_SCALE),
			);
		},
		[],
	);

	// Handle drag
	const handleMouseDown = useCallback(
		(e: React.MouseEvent) => {
			if (e.button !== 0) return; // Only left click
			setIsDragging(true);
			setDragStart({
				x: e.clientX - position.x,
				y: e.clientY - position.y,
			});
		},
		[position],
	);

	const handleMouseMove = useCallback(
		(e: React.MouseEvent) => {
			if (!isDragging) return;
			setPosition({
				x: e.clientX - dragStart.x,
				y: e.clientY - dragStart.y,
			});
		},
		[isDragging, dragStart],
	);

	const handleMouseUp = useCallback(() => {
		setIsDragging(false);
	}, []);

	const handleImageLoad = useCallback(
		(e: React.SyntheticEvent<HTMLImageElement>) => {
			setImageLoaded(true);
			setNaturalSize({
				width: e.currentTarget.naturalWidth,
				height: e.currentTarget.naturalHeight,
			});
		},
		[],
	);

	return (
		<div className="h-full flex flex-col">
			{/* Toolbar */}
			<div className="flex items-center justify-between px-4 py-2 border-b border-[color:var(--color-border)]/40 bg-[rgba(20,20,20,0.5)]">
				<div className="flex items-center gap-3">
					{/* Zoom controls */}
					<div className="flex items-center gap-1 rounded-lg border border-[color:var(--color-border)]/60 overflow-hidden">
						<button
							onClick={handleZoomOut}
							disabled={scale <= MIN_SCALE}
							className="p-1.5 text-[color:var(--color-text-secondary)] hover:text-slate-900 hover:bg-[color:var(--color-surface)]/50 transition-colors disabled:opacity-30"
							aria-label="Zoom out"
						>
							<Minus className="w-4 h-4" />
						</button>
						<span className="px-2 text-xs font-mono text-[color:var(--color-text-secondary)] min-w-[4rem] text-center">
							{Math.round(scale * 100)}%
						</span>
						<button
							onClick={handleZoomIn}
							disabled={scale >= MAX_SCALE}
							className="p-1.5 text-[color:var(--color-text-secondary)] hover:text-slate-900 hover:bg-[color:var(--color-surface)]/50 transition-colors disabled:opacity-30"
							aria-label="Zoom in"
						>
							<Plus className="w-4 h-4" />
						</button>
					</div>

					{/* Fit button */}
					<button
						onClick={handleFitToWindow}
						className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
							border border-[color:var(--color-border)]/60 text-[color:var(--color-text-secondary)]
							hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-slate-900
							transition-all"
					>
						<Minimize2 className="w-3.5 h-3.5" />
						Fit
					</button>

					{/* Reset button */}
					<button
						onClick={handleReset}
						className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
							border border-[color:var(--color-border)]/60 text-[color:var(--color-text-secondary)]
							hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-slate-900
							transition-all"
					>
						<RotateCcw className="w-3.5 h-3.5" />
						Reset
					</button>
				</div>

				{/* Image info */}
				{naturalSize.width > 0 && (
					<span className="text-xs text-[color:var(--color-text-muted)]">
						{naturalSize.width} × {naturalSize.height} px
					</span>
				)}
			</div>

			{/* Image container */}
			<div
				ref={containerRef}
				className="flex-1 overflow-hidden relative"
				onWheel={handleWheel}
				onMouseDown={handleMouseDown}
				onMouseMove={handleMouseMove}
				onMouseUp={handleMouseUp}
				onMouseLeave={handleMouseUp}
				style={{ cursor: isDragging ? "grabbing" : "grab" }}
			>
				{/* Checkered background for transparency */}
				<div
					className="absolute inset-0"
					style={{
						backgroundImage:
							"linear-gradient(45deg, rgba(30,30,30,1) 25%, transparent 25%), linear-gradient(-45deg, rgba(30,30,30,1) 25%, transparent 25%), linear-gradient(45deg, transparent 75%, rgba(30,30,30,1) 75%), linear-gradient(-45deg, transparent 75%, rgba(30,30,30,1) 75%)",
						backgroundSize: "20px 20px",
						backgroundPosition: "0 0, 0 10px, 10px -10px, -10px 0px",
						backgroundColor: "rgba(20,20,20,1)",
					}}
				/>

				{/* Image */}
				<div className="absolute inset-0 flex items-center justify-center">
					{imageError ? (
						<div className="flex flex-col items-center gap-4 text-center">
							<div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center">
								<ZoomIn className="w-8 h-8 text-red-400" />
							</div>
							<div>
								<p className="text-sm font-medium text-slate-900">
									Failed to load image
								</p>
								<p className="text-xs text-[color:var(--color-text-muted)]">
									{filename}
								</p>
							</div>
						</div>
					) : (
						<img
							src={src}
							alt={alt}
							onLoad={handleImageLoad}
							onError={() => setImageError(true)}
							style={{
								transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
								transition: isDragging ? "none" : "transform 0.1s ease-out",
								maxWidth: "none",
								maxHeight: "none",
							}}
							className="select-none"
							draggable={false}
						/>
					)}
				</div>

				{/* Loading overlay */}
				{!imageLoaded && !imageError && (
					<div className="absolute inset-0 flex items-center justify-center bg-black/50">
						<div className="w-8 h-8 rounded-full border-2 border-[rgba(var(--color-primary-rgb),0.35)] border-t-[color:var(--color-primary)] animate-spin" />
					</div>
				)}
			</div>
		</div>
	);
}
