"use client";

import { BookOpen, CheckCircle, PlayCircle, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { useTutorial } from "@/tutorial/TutorialContext";
import { TUTORIAL_DEFINITIONS } from "@/tutorial/steps";
import {
	getTutorialState,
	resetTutorial,
	resetAllTutorials,
} from "@/tutorial/persistence";

export default function TutorialsTab() {
	const { completedTutorials, refreshCompletionState } = useTutorial();
	const [lastStepReached, setLastStepReached] = useState<
		Record<string, number>
	>({});

	useEffect(() => {
		setLastStepReached(getTutorialState().lastStepReached);
	}, [completedTutorials]);

	const tutorials = Object.values(TUTORIAL_DEFINITIONS);

	const handleReset = (id: string) => {
		resetTutorial(id);
		refreshCompletionState();
		setLastStepReached(getTutorialState().lastStepReached);
	};

	const handleResetAll = () => {
		resetAllTutorials();
		refreshCompletionState();
		setLastStepReached({});
	};

	return (
		<div className="p-6">
			<div className="max-w-2xl">
				<div className="mb-6 flex items-start gap-3">
					<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
						<BookOpen className="h-5 w-5 text-orange-600" />
					</div>
					<div>
						<h3 className="mb-1 text-xl font-semibold tracking-tight text-slate-900">
							Tutorials
						</h3>
						<p className="text-sm text-slate-600">
							Reset your tutorial progress to replay any tutorial from the beginning. Tutorials guide
							you through key features of the application.
						</p>
					</div>
				</div>

				<div className="mb-6 overflow-hidden rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
					{tutorials.map((def, index) => (
						<div
							key={def.id}
							className={`flex items-center gap-3 px-4 py-3 transition-colors hover:bg-slate-50 ${
								index > 0 ? "border-t border-slate-200" : ""
							}`}
						>
							<span className="flex-shrink-0 text-lg text-slate-700" aria-hidden="true">
								{def.icon}
							</span>
							<span className="min-w-0 flex-1 font-medium text-slate-900">{def.label}</span>
							<span
								className={`flex flex-shrink-0 items-center gap-1 text-xs ${
									completedTutorials[def.id]
										? "text-emerald-700"
										: lastStepReached[def.id] != null && lastStepReached[def.id] > 0
											? "text-orange-700"
											: "text-slate-500"
								}`}
							>
								{completedTutorials[def.id] ? (
									<>
										<CheckCircle className="h-3.5 w-3.5" />
										Completed
									</>
								) : lastStepReached[def.id] != null && lastStepReached[def.id] > 0 ? (
									<>
										<PlayCircle className="h-3.5 w-3.5" />
										In progress — step {lastStepReached[def.id]}/{def.stepCount}
									</>
								) : (
									<>— Not started</>
								)}
							</span>
							<button
								type="button"
								onClick={() => handleReset(def.id)}
								aria-label={`Reset ${def.label} tutorial`}
								className="flex items-center gap-1 rounded-[4px] border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 transition-colors hover:border-orange-400 hover:bg-white hover:text-slate-900"
							>
								<RotateCcw className="h-3 w-3" />
								Reset
							</button>
						</div>
					))}
				</div>

				<button
					type="button"
					onClick={handleResetAll}
					className="flex items-center gap-2 rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-800 transition-colors hover:border-orange-400 hover:text-slate-900"
				>
					<RotateCcw className="h-4 w-4" />
					Reset all tutorials
				</button>
			</div>
		</div>
	);
}
