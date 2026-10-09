import { render, screen } from "@testing-library/react";
import StyledMarkdown from "./StyledMarkdown";

// Mock SyntaxHighlighter to avoid test complexity
jest.mock("react-syntax-highlighter", () => ({
	Prism: ({ children }: { children: string }) => <code>{children}</code>,
}));

jest.mock("react-syntax-highlighter/dist/esm/styles/prism", () => ({
	vscDarkPlus: {},
}));

describe("StyledMarkdown XSS Prevention", () => {
	describe("ISG PoC payload blocking", () => {
		it("blocks iframe with srcdoc containing script (ISG PoC payload)", () => {
			const xssPayload = `<iframe srcdoc="<script>alert(document.domain)</script>">`;
			const { container } = render(<StyledMarkdown content={xssPayload} />);

			// Verify no iframe element exists in the DOM
			const iframes = container.querySelectorAll("iframe");
			expect(iframes.length).toBe(0);

			// Verify no script tag exists
			const scripts = container.querySelectorAll("script");
			expect(scripts.length).toBe(0);

			// The content should not contain the dangerous payload
			expect(container.innerHTML).not.toContain("<iframe");
			expect(container.innerHTML).not.toContain("srcdoc");
			expect(container.innerHTML).not.toContain("<script>");
			expect(container.innerHTML).not.toContain("alert(");
		});

		it("blocks standalone iframe tags", () => {
			const xssPayload = `<iframe src="javascript:alert('XSS')"></iframe>`;
			const { container } = render(<StyledMarkdown content={xssPayload} />);

			expect(container.querySelectorAll("iframe").length).toBe(0);
			expect(container.innerHTML).not.toContain("javascript:");
		});
	});

	describe("Blocked tags", () => {
		it.each([
			["script", "<script>alert('XSS')</script>"],
			["iframe", "<iframe src='http://evil.com'></iframe>"],
			["object", "<object data='http://evil.com'></object>"],
			["embed", "<embed src='http://evil.com'>"],
			["form", "<form action='http://evil.com'><input></form>"],
			["input", "<input type='text' onfocus='alert(1)'>"],
		])("blocks %s tags", (tagName, payload) => {
			const { container } = render(<StyledMarkdown content={payload} />);
			expect(container.querySelectorAll(tagName).length).toBe(0);
		});

		it("blocks injected style tags with malicious CSS", () => {
			// The component has its own styled-jsx style tag, so we check the content is sanitized
			const payload = "<style>body { display: none; }</style>";
			const { container } = render(<StyledMarkdown content={payload} />);

			// Get all style tags - we should not find any with body { display: none }
			const styles = container.querySelectorAll("style");
			const hasInjectedStyle = Array.from(styles).some((s) =>
				s.textContent?.includes("display: none"),
			);
			expect(hasInjectedStyle).toBe(false);
		});
	});

	describe("Blocked event handler attributes", () => {
		it.each([
			["onclick", `<div onclick="alert('XSS')">Click me</div>`],
			["onerror", `<img src="x" onerror="alert('XSS')">`],
			["onload", `<body onload="alert('XSS')">Content</body>`],
			["onmouseover", `<span onmouseover="alert('XSS')">Hover</span>`],
			["onfocus", `<input onfocus="alert('XSS')">`],
			["onblur", `<input onblur="alert('XSS')">`],
		])("strips %s event handler", (handler, payload) => {
			const { container } = render(<StyledMarkdown content={payload} />);
			expect(container.innerHTML).not.toContain(handler);
			expect(container.innerHTML).not.toContain("alert(");
		});
	});

	describe("Safe content rendering", () => {
		it("renders basic markdown safely", () => {
			const safeContent = `# Hello World

This is **bold** and *italic* text.

- List item 1
- List item 2

[Safe link](https://example.com)`;

			render(<StyledMarkdown content={safeContent} />);

			expect(screen.getByText("Hello World")).toBeInTheDocument();
			expect(screen.getByText(/bold/)).toBeInTheDocument();
			expect(screen.getByText("Safe link")).toBeInTheDocument();
		});

		it("renders code blocks safely", () => {
			const codeContent = `\`\`\`javascript
const x = 1;
console.log(x);
\`\`\``;

			const { container } = render(<StyledMarkdown content={codeContent} />);

			// Code should render but not execute
			expect(container.textContent).toContain("const x = 1");
		});

		it("renders tables safely", () => {
			const tableContent = `| Header 1 | Header 2 |
| --- | --- |
| Cell 1 | Cell 2 |`;

			render(<StyledMarkdown content={tableContent} />);

			expect(screen.getByText("Header 1")).toBeInTheDocument();
			expect(screen.getByText("Cell 1")).toBeInTheDocument();
		});
	});

	describe("Variant styling", () => {
		it("applies light variant styling", () => {
			const { container } = render(
				<StyledMarkdown content="# Test" variant="light" />,
			);

			const heading = container.querySelector("h1");
			expect(heading).toHaveClass("text-slate-900");
		});

		it("applies default variant styling", () => {
			const { container } = render(
				<StyledMarkdown content="# Test" variant="default" />,
			);

			const heading = container.querySelector("h1");
			expect(heading).toHaveClass("text-white");
		});
	});

	describe("Complex XSS vectors", () => {
		it("blocks nested XSS attempts", () => {
			const nestedPayload = `<div><iframe srcdoc="<img src=x onerror=alert(1)>"></iframe></div>`;
			const { container } = render(<StyledMarkdown content={nestedPayload} />);

			expect(container.querySelectorAll("iframe").length).toBe(0);
			expect(container.innerHTML).not.toContain("onerror");
		});

		it("blocks data URI script execution", () => {
			const dataUriPayload = `<a href="data:text/html,<script>alert('XSS')</script>">Click</a>`;
			const { container } = render(<StyledMarkdown content={dataUriPayload} />);

			// The link should be sanitized or href should be safe
			const link = container.querySelector("a");
			if (link) {
				expect(link.getAttribute("href")).not.toContain("data:text/html");
			}
		});

		it("blocks javascript: protocol in links", () => {
			const jsPayload = `<a href="javascript:alert('XSS')">Click me</a>`;
			const { container } = render(<StyledMarkdown content={jsPayload} />);

			const link = container.querySelector("a");
			if (link) {
				expect(link.getAttribute("href")).not.toContain("javascript:");
			}
		});

		it("blocks svg with embedded script", () => {
			const svgPayload = `<svg onload="alert('XSS')"><circle r="10"></circle></svg>`;
			const { container } = render(<StyledMarkdown content={svgPayload} />);

			expect(container.innerHTML).not.toContain("onload");
			expect(container.innerHTML).not.toContain("alert(");
		});

		it("blocks base tag injection", () => {
			const basePayload = `<base href="http://evil.com/">`;
			const { container } = render(<StyledMarkdown content={basePayload} />);

			expect(container.querySelectorAll("base").length).toBe(0);
		});

		it("blocks meta refresh redirect", () => {
			const metaPayload = `<meta http-equiv="refresh" content="0;url=http://evil.com">`;
			const { container } = render(<StyledMarkdown content={metaPayload} />);

			expect(container.querySelectorAll("meta").length).toBe(0);
		});
	});
});
