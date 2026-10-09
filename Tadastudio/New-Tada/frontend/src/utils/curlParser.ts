/**
 * cURL command parser — Postman-style "import from cURL".
 *
 * Parses a pasted curl command into a normalized structure that can be
 * mapped onto the HTTP Request Action node configuration.
 *
 * Supports the flags that appear in real-world "Copy as cURL" output
 * (Chrome DevTools, Postman, API docs): -X/--request, -H/--header,
 * -d/--data(-raw|-binary|-ascii|-urlencode), -F/--form, -u/--user,
 * -b/--cookie, -A/--user-agent, -e/--referer, -G/--get, -I/--head,
 * -k/--insecure, --url, -m/--max-time, --retry, --oauth2-bearer.
 * Unknown flags are skipped and reported as warnings.
 */

export interface ParsedCurl {
	method: string;
	/** URL without the query string */
	url: string;
	/** Query params from the URL and -G data, in order of appearance */
	queryParams: Array<{ name: string; value: string }>;
	/** Headers excluding any Authorization header converted into `auth` */
	headers: Array<{ name: string; value: string }>;
	bodyType: "json" | "form" | "text" | "raw" | null;
	/** Raw body text (for json/text/raw). Empty string when no body. */
	body: string;
	/** Parsed body fields for form bodies and top-level JSON objects */
	bodyFields: Array<{ name: string; value: unknown }>;
	auth:
		| { type: "basic"; username: string; password: string }
		| { type: "bearer"; token: string }
		| null;
	verifySsl: boolean;
	timeoutSeconds?: number;
	maxRetries?: number;
	/** Non-fatal notes: unsupported flags, decode failures, etc. */
	warnings: string[];
}

/** Flags that consume the next token as their argument (or use =value). */
const ARG_FLAGS = new Set([
	"-X", "--request",
	"-H", "--header",
	"-d", "--data", "--data-raw", "--data-binary", "--data-ascii", "--data-urlencode",
	"-F", "--form", "--form-string",
	"-u", "--user",
	"-A", "--user-agent",
	"-e", "--referer",
	"-b", "--cookie",
	"--url",
	"-o", "--output",
	"-m", "--max-time",
	"--connect-timeout",
	"--retry",
	"-x", "--proxy",
	"--cacert", "--cert", "--key",
	"--oauth2-bearer",
	"-T", "--upload-file",
]);

/** Boolean flags that are safely ignored (with or without a warning). */
const IGNORED_FLAGS = new Set([
	"-L", "--location",
	"-s", "--silent",
	"-S", "--show-error",
	"-v", "--verbose",
	"-i", "--include",
	"-f", "--fail",
	"--compressed",
	"--http1.0", "--http1.1", "--http2", "--http3",
	"-#", "--progress-bar",
	"-g", "--globoff",
]);

/**
 * Tokenize a shell command string: whitespace-separated words honouring
 * single quotes, double quotes, backslash escapes, `$'...'` ANSI-C quoting
 * and backslash-newline / caret-newline line continuations.
 */
export function tokenizeShellCommand(input: string): string[] {
	// Normalize Windows cmd line continuations (^\n) and CRLF
	const src = input.replace(/\r\n/g, "\n").replace(/\^\n/g, " ");
	const tokens: string[] = [];
	let current = "";
	let hasCurrent = false;
	let i = 0;

	const pushCurrent = () => {
		if (hasCurrent) {
			tokens.push(current);
			current = "";
			hasCurrent = false;
		}
	};

	while (i < src.length) {
		const ch = src[i];

		if (ch === "\\") {
			// Backslash-newline = line continuation; otherwise escape next char
			if (src[i + 1] === "\n") {
				i += 2;
				continue;
			}
			if (i + 1 < src.length) {
				current += src[i + 1];
				hasCurrent = true;
				i += 2;
				continue;
			}
			i += 1;
			continue;
		}

		if (ch === "'") {
			// $'...' ANSI-C quoting is handled at the "$" branch below
			const end = src.indexOf("'", i + 1);
			if (end === -1) throw new Error("Unterminated single quote in command");
			current += src.slice(i + 1, end);
			hasCurrent = true;
			i = end + 1;
			continue;
		}

		if (ch === '"') {
			i += 1;
			let closed = false;
			while (i < src.length) {
				const c = src[i];
				if (c === "\\") {
					const next = src[i + 1];
					if (next === '"' || next === "\\" || next === "$" || next === "`") {
						current += next;
						i += 2;
					} else if (next === "\n") {
						i += 2; // continuation inside double quotes
					} else {
						current += c;
						i += 1;
					}
				} else if (c === '"') {
					closed = true;
					i += 1;
					break;
				} else {
					current += c;
					i += 1;
				}
			}
			if (!closed) throw new Error("Unterminated double quote in command");
			hasCurrent = true;
			continue;
		}

		if (ch === "$" && src[i + 1] === "'") {
			// ANSI-C quoted string: $'...\n...'
			i += 2;
			let out = "";
			let closed = false;
			while (i < src.length) {
				const c = src[i];
				if (c === "\\") {
					const next = src[i + 1];
					const simple: Record<string, string> = {
						n: "\n", t: "\t", r: "\r", "'": "'", '"': '"', "\\": "\\",
						a: "\x07", b: "\b", f: "\f", v: "\v", "0": "\0",
					};
					if (next in simple) {
						out += simple[next];
						i += 2;
					} else if (next === "x" && /^[0-9a-fA-F]{2}/.test(src.slice(i + 2, i + 4))) {
						out += String.fromCharCode(parseInt(src.slice(i + 2, i + 4), 16));
						i += 4;
					} else if (next === "u" && /^[0-9a-fA-F]{4}/.test(src.slice(i + 2, i + 6))) {
						out += String.fromCharCode(parseInt(src.slice(i + 2, i + 6), 16));
						i += 6;
					} else {
						out += c;
						i += 1;
					}
				} else if (c === "'") {
					closed = true;
					i += 1;
					break;
				} else {
					out += c;
					i += 1;
				}
			}
			if (!closed) throw new Error("Unterminated $'...' quote in command");
			current += out;
			hasCurrent = true;
			continue;
		}

		if (ch === " " || ch === "\t" || ch === "\n") {
			pushCurrent();
			i += 1;
			continue;
		}

		current += ch;
		hasCurrent = true;
		i += 1;
	}
	pushCurrent();
	return tokens;
}

function splitUrlQuery(rawUrl: string): {
	url: string;
	queryParams: Array<{ name: string; value: string }>;
} {
	const hashIndex = rawUrl.indexOf("#");
	const noHash = hashIndex === -1 ? rawUrl : rawUrl.slice(0, hashIndex);
	const qIndex = noHash.indexOf("?");
	if (qIndex === -1) return { url: noHash, queryParams: [] };

	const base = noHash.slice(0, qIndex);
	const query = noHash.slice(qIndex + 1);
	const queryParams: Array<{ name: string; value: string }> = [];
	for (const pair of query.split("&")) {
		if (!pair) continue;
		const eq = pair.indexOf("=");
		const name = eq === -1 ? pair : pair.slice(0, eq);
		const value = eq === -1 ? "" : pair.slice(eq + 1);
		queryParams.push({
			name: safeDecodeURIComponent(name),
			value: safeDecodeURIComponent(value),
		});
	}
	return { url: base, queryParams };
}

function safeDecodeURIComponent(value: string): string {
	try {
		return decodeURIComponent(value.replace(/\+/g, "%20"));
	} catch {
		return value;
	}
}

/** Parse a curl command string into a normalized request description. */
export function parseCurlCommand(input: string): ParsedCurl {
	const trimmed = input.trim();
	if (!trimmed) throw new Error("Command is empty");

	const tokens = tokenizeShellCommand(trimmed);
	if (tokens.length === 0) throw new Error("Command is empty");
	// Tolerate a leading "$ " prompt copied from docs
	if (tokens[0] === "$") tokens.shift();
	if (!tokens[0] || tokens[0].toLowerCase() !== "curl") {
		throw new Error('Not a curl command — it should start with "curl"');
	}
	tokens.shift();

	const result: ParsedCurl = {
		method: "",
		url: "",
		queryParams: [],
		headers: [],
		bodyType: null,
		body: "",
		bodyFields: [],
		auth: null,
		verifySsl: true,
		warnings: [],
	};

	let rawUrl = "";
	const dataParts: string[] = [];
	const urlencodeParts: string[] = [];
	const formFields: Array<{ name: string; value: string }> = [];
	let useGet = false;
	let isHead = false;
	let userArg: string | null = null;

	const takeArg = (flag: string, inlineValue: string | undefined, rest: string[]): string => {
		if (inlineValue !== undefined) return inlineValue;
		const next = rest.shift();
		if (next === undefined) throw new Error(`Flag ${flag} is missing its value`);
		return next;
	};

	const queue = [...tokens];
	while (queue.length > 0) {
		let token = queue.shift() as string;

		if (!token.startsWith("-") || token === "-") {
			// Positional argument = URL
			if (rawUrl) result.warnings.push(`Ignored extra argument: ${token}`);
			else rawUrl = token;
			continue;
		}

		// --flag=value form
		let inlineValue: string | undefined;
		if (token.startsWith("--")) {
			const eq = token.indexOf("=");
			if (eq !== -1) {
				inlineValue = token.slice(eq + 1);
				token = token.slice(0, eq);
			}
		} else if (token.length > 2) {
			// Combined short form: -XPOST, -HFoo
			const short = token.slice(0, 2);
			if (ARG_FLAGS.has(short)) {
				inlineValue = token.slice(2);
				token = short;
			}
		}

		switch (token) {
			case "-X":
			case "--request":
				result.method = takeArg(token, inlineValue, queue).toUpperCase();
				break;
			case "-H":
			case "--header": {
				const header = takeArg(token, inlineValue, queue);
				const colon = header.indexOf(":");
				if (colon === -1) {
					result.warnings.push(`Ignored malformed header: ${header}`);
					break;
				}
				const name = header.slice(0, colon).trim();
				const value = header.slice(colon + 1).trim();
				if (name) result.headers.push({ name, value });
				break;
			}
			case "-d":
			case "--data":
			case "--data-raw":
			case "--data-binary":
			case "--data-ascii": {
				let value = takeArg(token, inlineValue, queue);
				if (value.startsWith("@") && token !== "--data-raw") {
					result.warnings.push(
						`File reference "${value}" is not supported — paste the content inline`,
					);
					value = "";
				}
				if (value) dataParts.push(value);
				break;
			}
			case "--data-urlencode": {
				const value = takeArg(token, inlineValue, queue);
				urlencodeParts.push(value);
				break;
			}
			case "-F":
			case "--form":
			case "--form-string": {
				const value = takeArg(token, inlineValue, queue);
				const eq = value.indexOf("=");
				if (eq === -1) {
					result.warnings.push(`Ignored malformed form field: ${value}`);
					break;
				}
				const fieldName = value.slice(0, eq);
				let fieldValue = value.slice(eq + 1);
				if (fieldValue.startsWith("@") || fieldValue.startsWith("<")) {
					result.warnings.push(
						`Form file upload "${fieldName}" is not supported — configure it manually`,
					);
					fieldValue = "";
				}
				formFields.push({ name: fieldName, value: fieldValue });
				break;
			}
			case "-u":
			case "--user":
				userArg = takeArg(token, inlineValue, queue);
				break;
			case "--oauth2-bearer":
				result.auth = { type: "bearer", token: takeArg(token, inlineValue, queue) };
				break;
			case "-A":
			case "--user-agent":
				result.headers.push({ name: "User-Agent", value: takeArg(token, inlineValue, queue) });
				break;
			case "-e":
			case "--referer":
				result.headers.push({ name: "Referer", value: takeArg(token, inlineValue, queue) });
				break;
			case "-b":
			case "--cookie": {
				const value = takeArg(token, inlineValue, queue);
				if (value.includes("=")) result.headers.push({ name: "Cookie", value });
				else result.warnings.push(`Cookie file "${value}" is not supported`);
				break;
			}
			case "--url":
				rawUrl = takeArg(token, inlineValue, queue);
				break;
			case "-G":
			case "--get":
				useGet = true;
				break;
			case "-I":
			case "--head":
				isHead = true;
				break;
			case "-k":
			case "--insecure":
				result.verifySsl = false;
				break;
			case "-m":
			case "--max-time": {
				const seconds = Number(takeArg(token, inlineValue, queue));
				if (Number.isFinite(seconds) && seconds > 0) result.timeoutSeconds = Math.round(seconds);
				break;
			}
			case "--connect-timeout":
				takeArg(token, inlineValue, queue); // consume; overall timeout is what the node models
				break;
			case "--retry": {
				const retries = Number(takeArg(token, inlineValue, queue));
				if (Number.isFinite(retries) && retries >= 0) result.maxRetries = Math.round(retries);
				break;
			}
			default:
				if (ARG_FLAGS.has(token)) {
					takeArg(token, inlineValue, queue); // consume value, then warn
					result.warnings.push(`Flag ${token} is not supported and was ignored`);
				} else if (IGNORED_FLAGS.has(token)) {
					// silently fine
				} else {
					result.warnings.push(`Unknown flag ${token} was ignored`);
				}
		}
	}

	if (!rawUrl) throw new Error("No URL found in the curl command");
	// Accept scheme-less URLs the way curl does
	if (!/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(rawUrl)) rawUrl = `https://${rawUrl}`;

	const { url, queryParams } = splitUrlQuery(rawUrl);
	result.url = url;
	result.queryParams = queryParams;

	// --data-urlencode pieces: "name=value" or bare "value"
	const encodedPairs = urlencodeParts.map((part) => {
		const eq = part.indexOf("=");
		return eq === -1
			? { name: "", value: part }
			: { name: part.slice(0, eq), value: part.slice(eq + 1) };
	});

	const allData = [...dataParts, ...encodedPairs.map((p) => (p.name ? `${p.name}=${encodeURIComponent(p.value)}` : encodeURIComponent(p.value)))];

	if (useGet && allData.length > 0) {
		// -G moves data into the query string
		for (const part of allData.join("&").split("&")) {
			if (!part) continue;
			const eq = part.indexOf("=");
			result.queryParams.push({
				name: safeDecodeURIComponent(eq === -1 ? part : part.slice(0, eq)),
				value: eq === -1 ? "" : safeDecodeURIComponent(part.slice(eq + 1)),
			});
		}
	} else if (formFields.length > 0) {
		result.bodyType = "form";
		result.bodyFields = formFields;
	} else if (allData.length > 0) {
		const body = allData.join("&");
		result.body = body;
		const contentType =
			result.headers.find((h) => h.name.toLowerCase() === "content-type")?.value ?? "";

		let parsedJson: unknown;
		let isJson = false;
		try {
			parsedJson = JSON.parse(body);
			isJson = typeof parsedJson === "object" && parsedJson !== null;
		} catch {
			isJson = false;
		}

		if (isJson && !contentType.includes("x-www-form-urlencoded")) {
			result.bodyType = "json";
			if (!Array.isArray(parsedJson)) {
				result.bodyFields = Object.entries(parsedJson as Record<string, unknown>).map(
					([name, value]) => ({ name, value }),
				);
			}
		} else if (
			contentType.includes("x-www-form-urlencoded") ||
			(/^[^=&\s]+=[^&]*(&[^=&\s]+=[^&]*)*$/.test(body) && !contentType)
		) {
			result.bodyType = "form";
			result.bodyFields = body.split("&").map((pair) => {
				const eq = pair.indexOf("=");
				return {
					name: safeDecodeURIComponent(eq === -1 ? pair : pair.slice(0, eq)),
					value: eq === -1 ? "" : safeDecodeURIComponent(pair.slice(eq + 1)),
				};
			});
		} else {
			result.bodyType = "raw";
		}
	}

	// Auth: -u wins, then Authorization header (Bearer/Basic)
	if (userArg !== null) {
		const colon = userArg.indexOf(":");
		result.auth = {
			type: "basic",
			username: colon === -1 ? userArg : userArg.slice(0, colon),
			password: colon === -1 ? "" : userArg.slice(colon + 1),
		};
	} else if (!result.auth) {
		const authIndex = result.headers.findIndex(
			(h) => h.name.toLowerCase() === "authorization",
		);
		if (authIndex !== -1) {
			const value = result.headers[authIndex].value;
			const bearer = value.match(/^Bearer\s+(.+)$/i);
			const basic = value.match(/^Basic\s+(.+)$/i);
			if (bearer) {
				result.auth = { type: "bearer", token: bearer[1] };
				result.headers.splice(authIndex, 1);
			} else if (basic) {
				try {
					const decoded = atob(basic[1]);
					const colon = decoded.indexOf(":");
					result.auth = {
						type: "basic",
						username: colon === -1 ? decoded : decoded.slice(0, colon),
						password: colon === -1 ? "" : decoded.slice(colon + 1),
					};
					result.headers.splice(authIndex, 1);
				} catch {
					result.warnings.push(
						"Could not decode Basic auth credentials — kept as a header",
					);
				}
			}
			// Other Authorization schemes stay as plain headers
		}
	}

	// Method resolution: explicit -X > -I > implicit POST for body > GET
	if (!result.method) {
		if (isHead) result.method = "HEAD";
		else if (result.bodyType !== null) result.method = "POST";
		else result.method = "GET";
	}

	return result;
}
