import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import KeyboardShortcutsDialog from "./KeyboardShortcutsDialog";

// Mock createPortal to render children directly
jest.mock("react-dom", () => ({
	...jest.requireActual("react-dom"),
	createPortal: (node: React.ReactNode) => node,
}));

describe("KeyboardShortcutsDialog", () => {
	const mockOnClose = jest.fn();

	beforeEach(() => {
		mockOnClose.mockClear();
	});

	describe("Rendering", () => {
		it("renders when isOpen is true", () => {
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			expect(screen.getByRole("dialog")).toBeInTheDocument();
			expect(screen.getByText("Keyboard Shortcuts")).toBeInTheDocument();
		});

		it("does not render when isOpen is false", () => {
			render(<KeyboardShortcutsDialog isOpen={false} onClose={mockOnClose} />);

			expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
		});

		it("displays all shortcut categories", () => {
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			expect(screen.getByText("History")).toBeInTheDocument();
			expect(screen.getByText("Canvas")).toBeInTheDocument();
			expect(screen.getByText("Navigation")).toBeInTheDocument();
			expect(screen.getByText("Help")).toBeInTheDocument();
		});

		it("displays shortcut descriptions", () => {
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			expect(screen.getByText("Undo last action")).toBeInTheDocument();
			expect(screen.getByText("Redo last action")).toBeInTheDocument();
			// Delete selected node(s) or connection(s) appears twice - for Delete and Backspace keys
			expect(screen.getAllByText("Delete selected node(s) or connection(s)")).toHaveLength(2);
			expect(screen.getByText("Deselect all nodes")).toBeInTheDocument();
			expect(screen.getByText("Fit view to canvas")).toBeInTheDocument();
			expect(screen.getByText("Show this help dialog")).toBeInTheDocument();
		});

		it("displays keyboard shortcut keys", () => {
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			// Check for specific key badges (some keys appear multiple times)
			// Ctrl appears in multiple shortcuts (Ctrl+Z, Ctrl+Y, Ctrl+Shift+Z, Ctrl+0, Ctrl+Drag)
			expect(screen.getAllByText("Ctrl").length).toBeGreaterThan(0);
			// Z appears twice - Ctrl+Z and Ctrl+Shift+Z
			expect(screen.getAllByText("Z").length).toBeGreaterThan(0);
			expect(screen.getByText("Y")).toBeInTheDocument();
			expect(screen.getByText("Delete")).toBeInTheDocument();
			// Escape appears in both the shortcut list and the footer
			expect(screen.getAllByText("Escape").length).toBeGreaterThan(0);
			expect(screen.getByText("?")).toBeInTheDocument();
		});

		it("displays close button", () => {
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			expect(screen.getByRole("button", { name: /close/i })).toBeInTheDocument();
		});

		it("displays footer hint about closing", () => {
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			// The footer contains "Press" and "or click outside to close" with Esc kbd element between them
			expect(screen.getByText(/or click outside to close/i)).toBeInTheDocument();
			expect(screen.getByText("Esc")).toBeInTheDocument();
		});
	});

	describe("Interactions", () => {
		it("calls onClose when close button is clicked", async () => {
			const user = userEvent.setup();
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			const closeButton = screen.getByRole("button", { name: /close/i });
			await user.click(closeButton);

			expect(mockOnClose).toHaveBeenCalledTimes(1);
		});

		it("calls onClose when backdrop is clicked", async () => {
			const user = userEvent.setup();
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			// Click on the backdrop (the outer fixed div)
			const backdrop = screen.getByRole("dialog").parentElement;
			if (backdrop) {
				await user.click(backdrop);
				expect(mockOnClose).toHaveBeenCalledTimes(1);
			}
		});

		it("does not call onClose when dialog content is clicked", async () => {
			const user = userEvent.setup();
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			// Click on the dialog content itself
			const dialog = screen.getByRole("dialog");
			await user.click(dialog);

			expect(mockOnClose).not.toHaveBeenCalled();
		});

		it("calls onClose when Escape key is pressed", () => {
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			fireEvent.keyDown(document, { key: "Escape" });

			expect(mockOnClose).toHaveBeenCalledTimes(1);
		});
	});

	describe("Accessibility", () => {
		it("has proper dialog role and aria attributes", () => {
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			const dialog = screen.getByRole("dialog");
			expect(dialog).toHaveAttribute("aria-modal", "true");
			expect(dialog).toHaveAttribute("aria-labelledby", "shortcuts-dialog-title");
		});

		it("has a properly labeled title", () => {
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			const title = screen.getByText("Keyboard Shortcuts");
			expect(title).toHaveAttribute("id", "shortcuts-dialog-title");
		});

		it("close button has accessible label", () => {
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			const closeButton = screen.getByRole("button", { name: /close/i });
			expect(closeButton).toBeInTheDocument();
		});
	});

	describe("Body scroll lock", () => {
		it("prevents body scroll when dialog is open", () => {
			render(<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />);

			expect(document.body.style.overflow).toBe("hidden");
		});

		it("restores body scroll when dialog is closed", () => {
			const { rerender } = render(
				<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />
			);

			expect(document.body.style.overflow).toBe("hidden");

			rerender(<KeyboardShortcutsDialog isOpen={false} onClose={mockOnClose} />);

			expect(document.body.style.overflow).toBe("");
		});

		it("restores body scroll when unmounted", () => {
			const { unmount } = render(
				<KeyboardShortcutsDialog isOpen={true} onClose={mockOnClose} />
			);

			expect(document.body.style.overflow).toBe("hidden");

			unmount();

			expect(document.body.style.overflow).toBe("");
		});
	});
});
