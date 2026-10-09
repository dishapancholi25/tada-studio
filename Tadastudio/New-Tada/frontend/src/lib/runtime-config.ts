interface RuntimeConfig {
	apiUrl: string;
	deployment: "separate-domains" | "reverse-proxy";
	schedulingEnabled: boolean;
	timestamp: string;
}

class RuntimeConfigService {
	private config: RuntimeConfig | null = null;
	private configPromise: Promise<RuntimeConfig> | null = null;

	async getConfig(): Promise<RuntimeConfig> {
		// Return cached config if available
		if (this.config) {
			return this.config;
		}

		// Return ongoing fetch promise if already fetching
		if (this.configPromise) {
			return this.configPromise;
		}

		// Fetch config
		this.configPromise = this.fetchConfig();
		this.config = await this.configPromise;
		this.configPromise = null;

		return this.config;
	}

	private async fetchConfig(): Promise<RuntimeConfig> {
		try {
			const response = await fetch("/api/config", {
				cache: "force-cache", // Cache in the browser
			});

			if (!response.ok) {
				throw new Error(`Config fetch failed: ${response.status}`);
			}

			const config = await response.json();
			return {
				apiUrl: config.apiUrl ?? "",
				deployment:
					config.deployment ??
					(config.apiUrl ? "separate-domains" : "reverse-proxy"),
				schedulingEnabled: config.schedulingEnabled ?? false,
				timestamp: config.timestamp ?? new Date().toISOString(),
			};
		} catch (error) {
			// Fallback to relative paths if config fetch fails
			return {
				apiUrl: "",
				deployment: "reverse-proxy",
				schedulingEnabled: false,
				timestamp: new Date().toISOString(),
			};
		}
	}

	// Get API base URL
	async getApiBaseUrl(): Promise<string> {
		const config = await this.getConfig();
		return config.apiUrl;
	}

	// Get workflow scheduling feature toggle
	async isSchedulingEnabled(): Promise<boolean> {
		const config = await this.getConfig();
		return config.schedulingEnabled;
	}

	// Reset cache (useful for testing or forced refresh)
	resetCache(): void {
		this.config = null;
		this.configPromise = null;
	}
}

export const runtimeConfig = new RuntimeConfigService();
