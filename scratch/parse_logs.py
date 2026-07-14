import json
import os

log_path = r"C:\Users\theoi\.gemini\antigravity\brain\364af5fc-74ed-4982-a9de-47d08e607176\.system_generated\logs\transcript.jsonl"
if os.path.exists(log_path):
    print("Log file found. Parsing...")
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                # Check for run_command tool calls
                if "tool_calls" in obj:
                    for tc in obj["tool_calls"]:
                        if tc.get("name") == "run_command":
                            args = tc.get("args", {})
                            cmd = args.get("CommandLine", "")
                            if "python" in cmd or "uvicorn" in cmd:
                                print(f"Step {obj.get('step_index')}: {cmd}")
            except Exception as e:
                pass
else:
    print("Log file not found.")
