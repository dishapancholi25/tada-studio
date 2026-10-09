import type { TutorialDefinition } from "../types";
import { datasourcesTutorial } from "./datasources";
import { evaluationsTutorial } from "./evaluations";
import { executionsTutorial } from "./executions";
import { homeTutorial } from "./home";
import { libraryTutorial } from "./library";
import { publishTutorial } from "./publish";
import { settingsTutorial } from "./settings";

export const TUTORIAL_DEFINITIONS: Record<string, TutorialDefinition> = {
	home: homeTutorial,
	library: libraryTutorial,
	publish: publishTutorial,
	datasources: datasourcesTutorial,
	evaluations: evaluationsTutorial,
	executions: executionsTutorial,
	settings: settingsTutorial,
};
