"""Generates the compilation and __main__ block for the exported Python file."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.export.workflow_analyzer import WorkflowAnalysis


class MainGenerator:
    """Generates the app compilation and __main__ block."""

    def generate(self, analysis: WorkflowAnalysis) -> str:
        name = analysis.workflow_name

        return f'''# {"=" * 70}
# Compile & Run
# {"=" * 70}


graph = build_graph()
app = graph.compile()


if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        """Run the workflow."""
        # Accept input from command line arg or interactive prompt
        if len(sys.argv) > 1:
            user_input = " ".join(sys.argv[1:])
        else:
            user_input = input("Enter your message: ")

        initial_state = {{
            "messages": [HumanMessage(content=user_input)],
            "original_message": user_input,
            "node_outputs": {{}},
            "results": [],
            "current_node": None,
            "execution_id": "local-run",
            "graph_name": "{name}",
            "metadata": {{}},
            "execution_order": 0,
        }}
        result = await app.ainvoke(initial_state)
        print("\\n" + "=" * 60)
        print("Workflow Complete")
        print("=" * 60)
        # Print final node outputs
        for node_id, output in result.get("node_outputs", {{}}).items():
            raw = output.get("raw", "")
            print(f"\\n[{{node_id}}]:")
            print(raw)

    asyncio.run(main())'''
