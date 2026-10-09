/** Reusable section heading used by AIHealth, WorkflowPerformance, and any
 *  other widget that renders an orange-accent-bar title + subtitle outside of
 *  ChartContainer (which manages its own header internally). */
interface SectionHeaderProps {
	title: string;
	subtitle?: string;
	/** Optional element rendered flush-right (e.g. a coverage badge). */
	action?: React.ReactNode;
}

export default function SectionHeader({ title, subtitle, action }: SectionHeaderProps) {
	return (
		<div className="flex items-start justify-between gap-4">
			<div>
				<h2 className="flex items-center gap-2 text-[16px] font-semibold text-[#333333]">
					<span className="h-4 w-1 shrink-0 rounded-full bg-[#FF5E00]" />
					{title}
				</h2>
				{subtitle && (
					<p className="mt-0.5 pl-3 text-[12px] text-[#8A8A8A]">{subtitle}</p>
				)}
			</div>
			{action && <div className="shrink-0">{action}</div>}
		</div>
	);
}
