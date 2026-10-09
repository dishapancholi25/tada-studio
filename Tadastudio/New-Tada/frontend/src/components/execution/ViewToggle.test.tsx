import { render, screen, fireEvent } from "@testing-library/react";
import { useRouter } from "next/navigation";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ViewToggle from "./ViewToggle";

// Mock Next.js router
vi.mock("next/navigation", () => ({
	useRouter: vi.fn(),
}));

describe("ViewToggle", () => {
	const mockPush = vi.fn();
	const mockRouter = {
		push: mockPush,
	};

	beforeEach(() => {
		vi.clearAllMocks();
		(useRouter as ReturnType<typeof vi.fn>).mockReturnValue(mockRouter);
	});

	it("should render both Trace and Graph buttons", () => {
		render(
			<ViewToggle
				workflowId="test-workflow"
				executionId="test-execution"
				currentView="enhanced"
			/>,
		);

		expect(screen.getByTitle("Enhanced Trace View")).toBeInTheDocument();
		expect(screen.getByTitle("Graph View")).toBeInTheDocument();
		expect(screen.getByText("Trace")).toBeInTheDocument();
		expect(screen.getByText("Graph")).toBeInTheDocument();
	});

	it("should highlight the current view (enhanced)", () => {
		render(
			<ViewToggle
				workflowId="test-workflow"
				executionId="test-execution"
				currentView="enhanced"
			/>,
		);

		const traceButton = screen.getByTitle("Enhanced Trace View");
		expect(traceButton.className).toContain("text-[color:var(--color-primary)]");
	});

	it("should highlight the current view (graph)", () => {
		render(
			<ViewToggle
				workflowId="test-workflow"
				executionId="test-execution"
				currentView="graph"
			/>,
		);

		const graphButton = screen.getByTitle("Graph View");
		expect(graphButton.className).toContain("text-[color:var(--color-primary)]");
	});

	it("should navigate to enhanced view when clicking Trace button from graph view", () => {
		render(
			<ViewToggle
				workflowId="test-workflow"
				executionId="test-execution"
				currentView="graph"
			/>,
		);

		const traceButton = screen.getByTitle("Enhanced Trace View");
		fireEvent.click(traceButton);

		expect(mockPush).toHaveBeenCalledWith(
			"/workflow/test-workflow/test-execution",
		);
	});

	it("should navigate to graph view when clicking Graph button from enhanced view", () => {
		render(
			<ViewToggle
				workflowId="test-workflow"
				executionId="test-execution"
				currentView="enhanced"
			/>,
		);

		const graphButton = screen.getByTitle("Graph View");
		fireEvent.click(graphButton);

		expect(mockPush).toHaveBeenCalledWith(
			"/workflow/test-workflow/test-execution/graph",
		);
	});

	it("should preserve return query parameter when navigating", () => {
		render(
			<ViewToggle
				workflowId="test-workflow"
				executionId="test-execution"
				currentView="enhanced"
				returnParam="executions"
			/>,
		);

		const graphButton = screen.getByTitle("Graph View");
		fireEvent.click(graphButton);

		expect(mockPush).toHaveBeenCalledWith(
			"/workflow/test-workflow/test-execution/graph?return=executions",
		);
	});

	it("should encode workflowId in URL", () => {
		render(
			<ViewToggle
				workflowId="my workflow with spaces"
				executionId="test-execution"
				currentView="enhanced"
			/>,
		);

		const graphButton = screen.getByTitle("Graph View");
		fireEvent.click(graphButton);

		expect(mockPush).toHaveBeenCalledWith(
			"/workflow/my%20workflow%20with%20spaces/test-execution/graph",
		);
	});

	it("should encode executionId in URL", () => {
		render(
			<ViewToggle
				workflowId="test-workflow"
				executionId="exec-with-special-chars!@#"
				currentView="enhanced"
			/>,
		);

		const graphButton = screen.getByTitle("Graph View");
		fireEvent.click(graphButton);

		expect(mockPush).toHaveBeenCalledWith(
			"/workflow/test-workflow/exec-with-special-chars!%40%23/graph",
		);
	});

	it("should not navigate when clicking the currently active view", () => {
		render(
			<ViewToggle
				workflowId="test-workflow"
				executionId="test-execution"
				currentView="enhanced"
			/>,
		);

		const traceButton = screen.getByTitle("Enhanced Trace View");
		fireEvent.click(traceButton);

		expect(mockPush).not.toHaveBeenCalled();
	});

	it("should apply dark mode styles by default", () => {
		render(
			<ViewToggle
				workflowId="test-workflow"
				executionId="test-execution"
				currentView="enhanced"
			/>,
		);

		const traceButton = screen.getByTitle("Enhanced Trace View");
		expect(traceButton.className).toContain("text-[color:var(--color-primary)]");
	});

	it("should apply light mode styles when isDarkMode is false", () => {
		render(
			<ViewToggle
				workflowId="test-workflow"
				executionId="test-execution"
				currentView="graph"
				isDarkMode={false}
			/>,
		);

		const traceButton = screen.getByTitle("Enhanced Trace View");
		expect(traceButton.className).toContain("hover:bg-gray-100");
	});
});
