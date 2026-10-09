import { parseCurlCommand, tokenizeShellCommand } from "./curlParser";

describe("tokenizeShellCommand", () => {
	it("splits on whitespace", () => {
		expect(tokenizeShellCommand("curl -X POST url")).toEqual([
			"curl",
			"-X",
			"POST",
			"url",
		]);
	});

	it("honours single quotes", () => {
		expect(tokenizeShellCommand("curl -H 'X-Foo: a b c'")).toEqual([
			"curl",
			"-H",
			"X-Foo: a b c",
		]);
	});

	it("honours double quotes with escapes", () => {
		expect(tokenizeShellCommand('curl -d "{\\"a\\": 1}"')).toEqual([
			"curl",
			"-d",
			'{"a": 1}',
		]);
	});

	it("handles backslash-newline continuations", () => {
		expect(tokenizeShellCommand("curl \\\n  -X POST \\\n  url")).toEqual([
			"curl",
			"-X",
			"POST",
			"url",
		]);
	});

	it("handles $'...' ANSI-C quoting", () => {
		expect(tokenizeShellCommand("curl -d $'line1\\nline2'")).toEqual([
			"curl",
			"-d",
			"line1\nline2",
		]);
	});

	it("throws on unterminated quotes", () => {
		expect(() => tokenizeShellCommand("curl -H 'oops")).toThrow(
			/Unterminated single quote/,
		);
	});
});

describe("parseCurlCommand", () => {
	it("rejects non-curl input", () => {
		expect(() => parseCurlCommand("wget https://example.com")).toThrow(
			/should start with "curl"/,
		);
	});

	it("parses a bare GET", () => {
		const r = parseCurlCommand("curl https://api.example.com/users");
		expect(r.method).toBe("GET");
		expect(r.url).toBe("https://api.example.com/users");
		expect(r.queryParams).toEqual([]);
		expect(r.bodyType).toBeNull();
	});

	it("tolerates a copied '$ ' prompt and missing scheme", () => {
		const r = parseCurlCommand("$ curl api.example.com/health");
		expect(r.url).toBe("https://api.example.com/health");
	});

	it("extracts query params from the URL", () => {
		const r = parseCurlCommand(
			"curl 'https://api.example.com/search?q=hello%20world&page=2'",
		);
		expect(r.url).toBe("https://api.example.com/search");
		expect(r.queryParams).toEqual([
			{ name: "q", value: "hello world" },
			{ name: "page", value: "2" },
		]);
	});

	it("parses method, headers and JSON body (Chrome copy-as-curl shape)", () => {
		const r = parseCurlCommand(
			`curl 'https://api.example.com/v1/users' \\
  -X POST \\
  -H 'Content-Type: application/json' \\
  -H 'Accept: application/json' \\
  --data-raw '{"name": "Jane", "age": 30, "active": true}'`,
		);
		expect(r.method).toBe("POST");
		expect(r.headers).toEqual([
			{ name: "Content-Type", value: "application/json" },
			{ name: "Accept", value: "application/json" },
		]);
		expect(r.bodyType).toBe("json");
		expect(r.bodyFields).toEqual([
			{ name: "name", value: "Jane" },
			{ name: "age", value: 30 },
			{ name: "active", value: true },
		]);
	});

	it("implies POST when data is present without -X", () => {
		const r = parseCurlCommand("curl https://x.io -d 'a=1&b=2'");
		expect(r.method).toBe("POST");
		expect(r.bodyType).toBe("form");
		expect(r.bodyFields).toEqual([
			{ name: "a", value: "1" },
			{ name: "b", value: "2" },
		]);
	});

	it("supports combined short flags (-XPUT)", () => {
		const r = parseCurlCommand("curl -XPUT https://x.io/item/1");
		expect(r.method).toBe("PUT");
	});

	it("converts Authorization: Bearer into bearer auth and removes the header", () => {
		const r = parseCurlCommand(
			"curl https://x.io -H 'Authorization: Bearer abc123'",
		);
		expect(r.auth).toEqual({ type: "bearer", token: "abc123" });
		expect(r.headers).toEqual([]);
	});

	it("decodes Authorization: Basic into username/password", () => {
		// btoa("user:pass") === "dXNlcjpwYXNz"
		const r = parseCurlCommand(
			"curl https://x.io -H 'Authorization: Basic dXNlcjpwYXNz'",
		);
		expect(r.auth).toEqual({ type: "basic", username: "user", password: "pass" });
	});

	it("maps -u to basic auth", () => {
		const r = parseCurlCommand("curl -u admin:s3cret https://x.io");
		expect(r.auth).toEqual({
			type: "basic",
			username: "admin",
			password: "s3cret",
		});
	});

	it("parses multipart form fields and flags file uploads", () => {
		const r = parseCurlCommand(
			"curl https://x.io/upload -F name=doc -F file=@report.pdf",
		);
		expect(r.bodyType).toBe("form");
		expect(r.bodyFields).toEqual([
			{ name: "name", value: "doc" },
			{ name: "file", value: "" },
		]);
		expect(r.warnings.some((w) => w.includes("file upload"))).toBe(true);
	});

	it("moves -G data into query params", () => {
		const r = parseCurlCommand("curl -G https://x.io/search -d q=test -d page=3");
		expect(r.method).toBe("GET");
		expect(r.bodyType).toBeNull();
		expect(r.queryParams).toEqual([
			{ name: "q", value: "test" },
			{ name: "page", value: "3" },
		]);
	});

	it("maps -k, --max-time and --retry to advanced settings", () => {
		const r = parseCurlCommand(
			"curl -k --max-time 45 --retry 5 https://self-signed.local/api",
		);
		expect(r.verifySsl).toBe(false);
		expect(r.timeoutSeconds).toBe(45);
		expect(r.maxRetries).toBe(5);
	});

	it("keeps raw bodies that are not JSON objects or form pairs", () => {
		const r = parseCurlCommand(
			"curl https://x.io -H 'Content-Type: application/xml' -d '<user><name>J</name></user>'",
		);
		expect(r.bodyType).toBe("raw");
		expect(r.body).toBe("<user><name>J</name></user>");
	});

	it("treats cookies and user-agent as headers", () => {
		const r = parseCurlCommand(
			"curl https://x.io -b 'session=abc' -A 'MyAgent/1.0'",
		);
		expect(r.headers).toEqual(
			expect.arrayContaining([
				{ name: "Cookie", value: "session=abc" },
				{ name: "User-Agent", value: "MyAgent/1.0" },
			]),
		);
	});

	it("warns on unknown flags instead of failing", () => {
		const r = parseCurlCommand("curl --wat https://x.io");
		expect(r.url).toBe("https://x.io");
		expect(r.warnings.some((w) => w.includes("--wat"))).toBe(true);
	});

	it("maps -I to HEAD", () => {
		const r = parseCurlCommand("curl -I https://x.io");
		expect(r.method).toBe("HEAD");
	});

	it("handles --data-urlencode name=value", () => {
		const r = parseCurlCommand(
			"curl https://x.io --data-urlencode 'msg=hello world'",
		);
		expect(r.bodyType).toBe("form");
		expect(r.bodyFields).toEqual([{ name: "msg", value: "hello world" }]);
	});

	it("parses a realistic Postman-style export", () => {
		const r = parseCurlCommand(
			`curl --location --request PATCH 'https://api.example.com/v2/orders/42?notify=true' \\
--header 'Authorization: Bearer eyJtoken' \\
--header 'Content-Type: application/json' \\
--data-raw '{
    "status": "shipped",
    "items": [{"sku": "A1", "qty": 2}]
}'`,
		);
		expect(r.method).toBe("PATCH");
		expect(r.url).toBe("https://api.example.com/v2/orders/42");
		expect(r.queryParams).toEqual([{ name: "notify", value: "true" }]);
		expect(r.auth).toEqual({ type: "bearer", token: "eyJtoken" });
		expect(r.bodyType).toBe("json");
		expect(r.bodyFields).toEqual([
			{ name: "status", value: "shipped" },
			{ name: "items", value: [{ sku: "A1", qty: 2 }] },
		]);
	});
});

describe("parseCurlCommand — nested JSON bodies", () => {
	it("reports object values so callers can preserve structure", () => {
		const r = parseCurlCommand(
			`curl -X POST https://api.example.com/crm \\
  -H 'Content-Type: application/json' \\
  -d '{"headerJson":{"Header":{"Location":"AE","Source":"TADA"}},"inputParametersJson":{"Records":{"Param":[{"Name":"CreatedOn"}]}}}'`,
		);

		expect(r.bodyType).toBe("json");
		// Values stay structured — the panel decides field mappings vs raw body
		expect(r.bodyFields).toEqual([
			{ name: "headerJson", value: { Header: { Location: "AE", Source: "TADA" } } },
			{
				name: "inputParametersJson",
				value: { Records: { Param: [{ Name: "CreatedOn" }] } },
			},
		]);
		// The exact original payload is always available verbatim
		expect(JSON.parse(r.body)).toEqual({
			headerJson: { Header: { Location: "AE", Source: "TADA" } },
			inputParametersJson: { Records: { Param: [{ Name: "CreatedOn" }] } },
		});
	});

	it("keeps flat JSON values scalar", () => {
		const r = parseCurlCommand(
			`curl -X POST https://x.io -H 'Content-Type: application/json' -d '{"a":1,"b":"two","c":true}'`,
		);

		expect(r.bodyFields.every((f) => typeof f.value !== "object")).toBe(true);
	});
});
