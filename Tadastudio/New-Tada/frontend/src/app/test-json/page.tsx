"use client";

import React from "react";
import JsonViewerEnhanced from "@/components/JsonViewerEnhanced";

export default function TestJsonPage() {
	// Test data similar to the screenshot example
	const tokyoData = {
		Destinations: [
			"Meiji Shrine",
			"Harajuku's Takeshita Street",
			"Asakusa and Senso-ji Temple",
			"Tokyo Skytree",
			"Shibuya Crossing & Hachiko Statue",
			"Akihabara",
			"TeamLab Planets or Borderless",
			"Odaiba",
			"Tsukiji Outer Market",
			"Hamarikyu Gardens",
			"Ginza Shopping District",
			"Tokyo Imperial Palace East Gardens",
			"Shinjuku",
		],
		Foods: [
			"Crepes",
			"Traditional Japanese snacks",
			"Sushi Dai",
			"Ichiran Ramen",
			"Seafood breakfast at Tsukiji Outer Market",
			"Tonkatsu at Maisen",
			"Sushi no Midori",
			"Tempura Kondo",
			"Takoyaki at Ameya-Yokocho Market",
		],
	};

	// Raw response format (JSON string inside response field)
	const rawResponseData = {
		response:
			'{\n  "Destinations": [\n    "Senso-ji Temple in Asakusa",\n    "Nakamise Shopping Street",\n    "Sumida River",\n    "Tokyo Skytree",\n    "Solamachi shopping complex",\n    "Ueno Park",\n    "Ameyoko Market",\n    "Odaiba",\n    "Meiji Shrine",\n    "Harajuku\'s Takeshita Street",\n    "Shibuya Crossing",\n    "Hachiko Statue",\n    "Shibuya Sky",\n    "Shinjuku",\n    "Omoide Yokocho",\n    "Golden Gai",\n    "Robot Restaurant",\n    "Hamarikyu Gardens",\n    "Akihabara",\n    "Ginza",\n    "Roppongi Hills",\n    "Tokyo Tower"\n  ],\n  "Foods": [\n    "Sushi at Tsukiji Outer Market",\n    "Soba noodles at Kanda Matsuya",\n    "Tempura at Tempura Kondo",\n    "Traditional kaiseki meal at Ishikawa",\n    "Casual dining at Nadaman",\n    "Retro coffee shop like Café de L\'Ambre",\n    "Ramen at Ichiran or Tsuta Ramen",\n    "Harajuku street food like crepes or rainbow cotton candy",\n    "Izakaya dining at Toritake in Shibuya",\n    "Uoshin Nogizaka for fresh seafood",\n    "Anpan from Kimuraya Bakery",\n    "Monjayaki in Tsukishima Monja Street",\n    "Depachika delights like bento boxes and Japanese pastries",\n    "Sushi at Sukiyabashi Jiro",\n    "Yakiniku at Yoroniku"\n  ]\n}',
	};

	// Complex nested structure
	const complexData = {
		user: {
			id: 12345,
			name: "John Doe",
			email: "john.doe@example.com",
			active: true,
			metadata: {
				created_at: "2024-01-15T10:30:00Z",
				updated_at: "2024-03-20T15:45:00Z",
				tags: ["premium", "verified", "early_adopter"],
				settings: {
					theme: "dark",
					notifications: {
						email: true,
						push: false,
						sms: true,
					},
					privacy: {
						profile_visible: true,
						show_email: false,
					},
				},
			},
		},
		orders: [
			{
				order_id: "ORD-001",
				date: "2024-03-15",
				total: 249.99,
				status: "delivered",
				items: [
					{ name: "Widget A", quantity: 2, price: 49.99 },
					{ name: "Widget B", quantity: 1, price: 150.01 },
				],
			},
			{
				order_id: "ORD-002",
				date: "2024-03-18",
				total: 89.5,
				status: "processing",
				items: [{ name: "Gadget X", quantity: 3, price: 29.83 }],
			},
		],
		stats: {
			total_spent: 339.49,
			average_order: 169.75,
			member_since_days: 365,
		},
	};

	// Array of objects (good for table view)
	const tableData = [
		{
			id: 1,
			name: "Alice Johnson",
			age: 28,
			city: "New York",
			role: "Developer",
			salary: 95000,
		},
		{
			id: 2,
			name: "Bob Smith",
			age: 35,
			city: "San Francisco",
			role: "Designer",
			salary: 88000,
		},
		{
			id: 3,
			name: "Carol White",
			age: 42,
			city: "Chicago",
			role: "Manager",
			salary: 120000,
		},
		{
			id: 4,
			name: "David Brown",
			age: 29,
			city: "Austin",
			role: "Developer",
			salary: 92000,
		},
		{
			id: 5,
			name: "Eve Davis",
			age: 31,
			city: "Seattle",
			role: "Product Owner",
			salary: 105000,
		},
		{
			id: 6,
			name: "Frank Miller",
			age: 38,
			city: "Boston",
			role: "Architect",
			salary: 135000,
		},
		{
			id: 7,
			name: "Grace Wilson",
			age: 26,
			city: "Denver",
			role: "Developer",
			salary: 85000,
		},
		{
			id: 8,
			name: "Henry Taylor",
			age: 45,
			city: "Portland",
			role: "Director",
			salary: 150000,
		},
	];

	// Long string test
	const longStringData = {
		message:
			"This is a very long message that contains a lot of text to test how the component handles text truncation and expansion. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
		shortMessage: "This is a short message",
		metadata: {
			timestamp: "2024-03-20T10:30:00Z",
			version: "1.0.0",
		},
	};

	return (
		<div className="min-h-screen bg-slate-50 text-slate-900 p-8">
			<h1 className="text-2xl font-bold mb-8">JSON Viewer Test Page</h1>

			<div className="space-y-8">
				{/* Raw Response Format (as in the actual screenshot) */}
				<section>
					<h2 className="text-lg font-semibold mb-3">
						Raw Response Format (JSON string in response field)
					</h2>
					<JsonViewerEnhanced data={rawResponseData} />
				</section>

				{/* Tokyo Data Example */}
				<section>
					<h2 className="text-lg font-semibold mb-3">
						Tokyo Travel Data (direct object)
					</h2>
					<JsonViewerEnhanced data={tokyoData} />
				</section>

				{/* Complex Nested Structure */}
				<section>
					<h2 className="text-lg font-semibold mb-3">
						Complex Nested Structure
					</h2>
					<JsonViewerEnhanced data={complexData} />
				</section>

				{/* Table Data */}
				<section>
					<h2 className="text-lg font-semibold mb-3">
						Array of Objects (Table View Available)
					</h2>
					<JsonViewerEnhanced data={tableData} />
				</section>

				{/* Long String Test */}
				<section>
					<h2 className="text-lg font-semibold mb-3">Long String Handling</h2>
					<JsonViewerEnhanced data={longStringData} />
				</section>

				{/* Primitive Values */}
				<section>
					<h2 className="text-lg font-semibold mb-3">Primitive Values</h2>
					<div className="space-y-2">
						<div>
							<span className="text-[color:var(--color-text-muted)] mr-2">
								String:
							</span>
							<JsonViewerEnhanced data="Hello World" />
						</div>
						<div>
							<span className="text-[color:var(--color-text-muted)] mr-2">
								Number:
							</span>
							<JsonViewerEnhanced data={42} />
						</div>
						<div>
							<span className="text-[color:var(--color-text-muted)] mr-2">
								Boolean:
							</span>
							<JsonViewerEnhanced data={true} />
						</div>
						<div>
							<span className="text-[color:var(--color-text-muted)] mr-2">
								Null:
							</span>
							<JsonViewerEnhanced data={null} />
						</div>
					</div>
				</section>

				{/* Empty Collections */}
				<section>
					<h2 className="text-lg font-semibold mb-3">Empty Collections</h2>
					<div className="space-y-2">
						<JsonViewerEnhanced data={{}} />
						<JsonViewerEnhanced data={[]} />
					</div>
				</section>
			</div>
		</div>
	);
}
