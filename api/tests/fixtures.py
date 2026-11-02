"""A valid page used across tests."""

SOURCE_URL = "https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/compute-decision-tree"


def valid_page(source_url: str = SOURCE_URL) -> dict:
    return {
        "title": "Azure compute options",
        "summary": "Azure offers several ways to run code, from full VMs to fully managed serverless functions.",
        "overview": "Azure compute services run your application code.\n\nPick based on control versus management effort.",
        "diagram": {
            "caption": "From most control to least",
            "mermaid": "flowchart LR\n  VM[\"Virtual Machines\"] --> AKS --> ACA[\"Container Apps\"] --> FN[\"Functions\"]",
        },
        "keyConcepts": [
            {"term": "IaaS", "explanation": "You manage the OS."},
            {"term": "PaaS", "explanation": "Azure manages the platform."},
            {"term": "Serverless", "explanation": "Pay per execution."},
            {"term": "Container", "explanation": "Packaged app and dependencies."},
        ],
        "comparison": {
            "caption": "Compute options",
            "columns": ["Service", "Control", "Best for"],
            "rows": [
                ["Virtual Machines", "Full", "Lift and shift"],
                ["App Service", "Medium", "Web apps"],
                ["Functions", "Low", "Event-driven code"],
            ],
        },
        "whenToUse": [
            {"option": "Virtual Machines", "useWhen": "You need OS-level control."},
            {"option": "Functions", "useWhen": "Short event-driven tasks."},
        ],
        "pitfalls": ["Over-sizing VMs", "Ignoring cold starts", "Skipping autoscale"],
        "quiz": [
            {
                "question": f"Q{i}",
                "options": ["a", "b", "c", "d"],
                "answerIndex": i % 4,
                "explanation": "Because.",
            }
            for i in range(3)
        ],
        "sources": [{"title": "Choose a compute service", "url": source_url}],
    }
