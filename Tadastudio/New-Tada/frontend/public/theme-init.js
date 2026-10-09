(() => {
	try {
		// Read the persisted theme from the cookie first (fastest, matches what
		// the SSR server reads via the request Cookie header).
		var cookieMatch = document.cookie.match(
			/(?:^|;\s*)agenticstudio-color-theme=([^;]+)/,
		);
		var theme = cookieMatch ? decodeURIComponent(cookieMatch[1]) : null;

		// Migrate / remove legacy slugs.
		if (theme === "plum") theme = "expose";
		if (theme === "legacy" || theme === "synechron") theme = null;

		// Fall back to localStorage when the cookie is absent.
		if (theme !== "expose" && theme !== "mashreq") {
			try {
				var stored = window.localStorage.getItem("agenticstudio-color-theme");
				if (stored === "plum") stored = "expose";
				if (stored === "legacy" || stored === "synechron") stored = null;
				theme = stored === "expose" ? "expose" : "mashreq";
			} catch (_) {
				theme = "mashreq";
			}
		}

		// Stamp the theme on <html> before any CSS renders so the first painted
		// frame already has the correct CSS variable block active (no FOUC).
		document.documentElement.dataset.colorTheme = theme || "mashreq";

		// Show the loading overlay on workflow detail pages to hide the
		// hydration flash while the heavy graph editor boots up.
		var p = (window.location && window.location.pathname) || "";
		if (p.indexOf("/workflow/") === 0) {
			document.documentElement.classList.add("ssr-overlay-active");
		} else {
			document.documentElement.classList.remove("ssr-overlay-active");
		}
	} catch (_) {}
})();
