with open("main.py", "r", encoding="utf-8") as f:
    main_content = f.read()

print("Search in main.py:")
if "Combined" in main_content:
    print("  Found 'Combined' in main.py!")
    # Stampa le righe con 'Combined'
    lines = main_content.splitlines()
    for i, l in enumerate(lines):
        if "Combined" in l:
            print(f"    Line {i+1}: {l.strip()}")
else:
    print("  'Combined' not found in main.py")

try:
    with open("summary.py", "r", encoding="utf-8") as f:
        summary_content = f.read()
    print("Search in summary.py:")
    if "Combined" in summary_content:
        print("  Found 'Combined' in summary.py!")
        lines = summary_content.splitlines()
        for i, l in enumerate(lines):
            if "Combined" in l:
                print(f"    Line {i+1}: {l.strip()}")
except Exception as e:
    print("Error reading summary.py:", e)
