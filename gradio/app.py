"""
Gradio Frontend for Process Engine Performance Analyzer
Natural Language Query Interface
"""

import gradio as gr
import requests
import json
import pandas as pd
from typing import Tuple, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# FastAPI service URL (read from environment variable, default to localhost)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def format_markdown_list(items: list) -> str:
    """Format list as Markdown"""
    if not items:
        return "_No information available_"
    return "\n".join([f"- {item}" for item in items])


def format_visualization_suggestions(viz_list: list) -> str:
    """Format visualization suggestions"""
    if not viz_list:
        return "_No visualization suggestions available_"

    result = []
    for i, viz in enumerate(viz_list, 1):
        result.append(f"### Suggestion {i}: {viz.get('title', 'Untitled Chart')}")
        result.append(f"**Chart Type**: {viz.get('chart_type', 'N/A')}")
        result.append(f"**Description**: {viz.get('description', 'N/A')}")
        result.append(f"**X-Axis**: {viz.get('x_axis', 'N/A')}")
        result.append(f"**Y-Axis**: {viz.get('y_axis', 'N/A')}")
        result.append("")

    return "\n".join(result)


def query_analysis(user_query: str) -> Tuple[str, str, str, str, str, str, str]:
    """
    Call API and return results

    Returns:
        Tuple of (status, sql, dataframe_html, summary, findings, recommendations, visualizations)
    """
    if not user_query or not user_query.strip():
        return (
            "WARNING: Please enter a query",
            "",
            "",
            "",
            "",
            "",
            ""
        )

    try:
        # Call API
        response = requests.post(
            f"{API_BASE_URL}/api/v1/analysis/query",
            json={"query": user_query.strip()},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        # Check success status
        success = data.get("success", False)

        if not success:
            error_msg = data.get("error", "Unknown error")
            error_stage = data.get("error_stage", "unknown")
            return (
                f"FAILED (Stage: {error_stage})",
                "",
                f"### Error Message\n\n{error_msg}",
                "",
                "",
                "",
                ""
            )

        # Extract data
        sql = data.get("sql", "")
        results = data.get("results", [])
        row_count = data.get("row_count", 0)
        execution_time = data.get("execution_time_ms", 0)

        analysis = data.get("analysis", {})
        summary = analysis.get("summary", "")
        findings = analysis.get("key_findings", [])
        recommendations = analysis.get("recommendations", [])
        visualizations = analysis.get("visualization_suggestions", [])

        # Build status message
        status = f"SUCCESS | {row_count} rows | {execution_time:.2f}ms"

        # Build data table
        if results:
            try:
                df = pd.DataFrame(results)
                # Convert to HTML table with styling
                dataframe_html = df.to_html(
                    index=False,
                    classes='dataframe',
                    border=0,
                    max_rows=100
                )
            except Exception as e:
                dataframe_html = f"WARNING: Data formatting failed: {str(e)}\n\n```json\n{json.dumps(results[:5], indent=2, ensure_ascii=False)}\n```"
        else:
            dataframe_html = "**Query returned 0 rows**\n\nThis might be normal (no matching data) or you may need to adjust query conditions. Check the AI analysis below for suggestions."

        # Format analysis results
        findings_md = format_markdown_list(findings)
        recommendations_md = format_markdown_list(recommendations)
        visualizations_md = format_visualization_suggestions(visualizations)

        return (
            status,
            sql,
            dataframe_html,
            summary,
            findings_md,
            recommendations_md,
            visualizations_md
        )

    except requests.exceptions.ConnectionError:
        error_msg = f"""
### Connection Failed

**Checklist:**
1. Ensure FastAPI service is running
   ```bash
   ./start.sh
   # or
   python -m app.main
   ```

2. Verify API address is correct: `{API_BASE_URL}`

3. Check if port 8000 is in use
   ```bash
   lsof -i :8000
   ```
"""
        return ("CONNECTION FAILED", "", error_msg, "", "", "", "")

    except requests.exceptions.Timeout:
        error_msg = "### Query Timeout\n\nQuery execution exceeded 60 seconds. Possible causes:\n- Query is too complex\n- Database connection is slow\n- Data volume is too large\n\nTry simplifying the query or contact administrator."
        return ("QUERY TIMEOUT", "", error_msg, "", "", "", "")

    except Exception as e:
        error_msg = f"### System Error\n\n```\n{str(e)}\n```"
        return ("SYSTEM ERROR", "", error_msg, "", "", "", "")


def test_connection() -> str:
    """Test API connection"""
    try:
        response = requests.get(f"{API_BASE_URL}/ping", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return f"Backend connection OK\n\nAPI Address: {API_BASE_URL}\nStatus: {data.get('status', 'ok')}\nTimestamp: {data.get('timestamp', 'N/A')}"
        else:
            return f"Backend response abnormal (Status code: {response.status_code})\n\nAPI Address: {API_BASE_URL}"
    except:
        return f"Unable to connect to backend\n\nAPI Address: {API_BASE_URL}\n\nPlease ensure backend service is running."


# Preset query examples
EXAMPLES = [
    ["Show top 5 processes with highest failure rate in the past 7 days"],
    ["Analyze hourly time-series trends of process execution"],
    ["Compare process execution performance between yesterday and today"],
    ["Find activities with average execution time over 10 seconds"],
    ["Which processes have the largest variable data?"],
    ["Calculate daily success rate for the past week"],
    ["Find the 10 slowest process instances"],
]


# Custom CSS styles
custom_css = """
.dataframe {
    font-size: 14px;
    width: 100%;
    border-collapse: collapse;
}
.dataframe th {
    background-color: #f0f0f0;
    padding: 8px;
    text-align: left;
    border-bottom: 2px solid #ddd;
    font-weight: 600;
}
.dataframe td {
    padding: 8px;
    border-bottom: 1px solid #eee;
}
.dataframe tr:hover {
    background-color: #f5f5f5;
}
"""


# Create Gradio interface
with gr.Blocks(
    title="Process Engine Performance Analyzer",
    theme=gr.themes.Soft(),
    css=custom_css
) as demo:

    # Title and description
    gr.Markdown(
        """
        # Process Engine Performance Analyzer

        **Natural Language Query System** - Enter questions in natural language to automatically generate SQL and receive AI analysis

        ---
        """
    )

    # Connection status check
    with gr.Row():
        with gr.Column(scale=4):
            gr.Markdown("### System Status")
        with gr.Column(scale=1):
            connection_btn = gr.Button("Test Connection", size="sm")

    connection_status = gr.Markdown("")

    connection_btn.click(
        fn=test_connection,
        outputs=connection_status
    )

    gr.Markdown("---")

    # Query input area
    with gr.Row():
        query_input = gr.Textbox(
            label="Enter Natural Language Query",
            placeholder="Example: Show top 5 processes with highest failure rate in the past 7 days",
            lines=3,
            scale=4
        )

    with gr.Row():
        clear_btn = gr.Button("Clear", size="sm")
        submit_btn = gr.Button("Query", variant="primary", size="lg", scale=2)

    # Example queries
    gr.Examples(
        examples=EXAMPLES,
        inputs=query_input,
        label="Click examples for quick queries",
        examples_per_page=7
    )

    # Query status
    status_output = gr.Markdown(label="Status")

    gr.Markdown("---")

    # Results display area - using tabs
    with gr.Tabs():

        # Tab 1: SQL and Data
        with gr.Tab("SQL & Data"):
            with gr.Row():
                sql_output = gr.Code(
                    label="Generated SQL Query",
                    language="sql",
                    lines=12,
                    interactive=False
                )

            with gr.Row():
                data_output = gr.HTML(label="Query Results")

        # Tab 2: AI Analysis
        with gr.Tab("AI Analysis"):
            summary_output = gr.Markdown(label="Executive Summary")

            with gr.Accordion("Key Findings", open=True):
                findings_output = gr.Markdown()

            with gr.Accordion("Optimization Recommendations", open=True):
                recommendations_output = gr.Markdown()

            with gr.Accordion("Visualization Suggestions", open=False):
                visualizations_output = gr.Markdown()

    # Footer information
    gr.Markdown(
        """
        ---

        ### Usage Tips

        1. **Enter natural language query**: Describe the data analysis you want in plain language
        2. **Click Query button**: System will automatically generate SQL, execute query, and analyze results
        3. **View results**: Check SQL, data, and AI analysis in different tabs

        ### System Features

        - Automatic SQL generation (powered by Claude AI)
        - SQL security validation (prevents data corruption)
        - PostgreSQL 9.6 compatibility handling
        - AI-powered analysis (performance bottlenecks, optimization suggestions)
        - Visualization recommendations (chart types, metric selection)

        ### Data Tables

        - `pe_ext_procinst`: Process instance table (execution records, status, timestamps)
        - `pe_ext_actinst`: Activity instance table (process step details)
        - `pe_ext_varinst`: Variable instance table (process variable data)

        ---
        **Version**: 1.0.0 | **Backend API**: `{}`
        """.format(API_BASE_URL)
    )

    # Bind events
    outputs_list = [
        status_output,
        sql_output,
        data_output,
        summary_output,
        findings_output,
        recommendations_output,
        visualizations_output
    ]

    submit_btn.click(
        fn=query_analysis,
        inputs=[query_input],
        outputs=outputs_list
    )

    # Support Enter key submission
    query_input.submit(
        fn=query_analysis,
        inputs=[query_input],
        outputs=outputs_list
    )

    # Clear button
    clear_btn.click(
        fn=lambda: ("", "", "", "", "", "", ""),
        outputs=outputs_list
    )


if __name__ == "__main__":
    print("=" * 60)
    print("  Process Engine Performance Analyzer - Gradio Frontend")
    print("=" * 60)
    print(f"Backend API: {API_BASE_URL}")
    print("Gradio interface is starting...")
    print("=" * 60)
    print()

    demo.launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=7860,       # Gradio default port
        share=False,            # Set to True for public link
        show_error=True,        # Show detailed error messages
        favicon_path=None
    )
